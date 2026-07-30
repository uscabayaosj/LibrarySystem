"""Tests for self-service loan renewal."""
from datetime import datetime, timedelta

from models import Borrowing, Reservation, User
from tests.conftest import login


def _active_loan(db, user, book, due_in_days=5, renewal_count=0):
    b = Borrowing(
        user_id=user.id, book_id=book.id,
        due_date=datetime.utcnow() + timedelta(days=due_in_days),
        status='active', renewal_count=renewal_count,
    )
    db.session.add(b)
    db.session.commit()
    return b


# ---- Model-level rules -------------------------------------------------------

def test_can_renew_a_loan_in_good_standing(db, member, book):
    loan = _active_loan(db, member, book)
    assert loan.can_renew is True
    assert loan.renew_blocked_reason is None


def test_cannot_renew_an_overdue_loan(db, member, book):
    loan = _active_loan(db, member, book, due_in_days=-3)
    assert loan.can_renew is False
    assert 'returned' in loan.renew_blocked_reason.lower()


def test_cannot_renew_past_the_renewal_limit(app, db, member, book):
    max_renewals = app.config['MAX_RENEWALS']
    loan = _active_loan(db, member, book, renewal_count=max_renewals)
    assert loan.can_renew is False
    assert 'limit' in loan.renew_blocked_reason.lower()
    assert loan.renewals_remaining == 0


def test_cannot_renew_when_another_member_is_waiting(db, member, book):
    loan = _active_loan(db, member, book)

    waiter = User(username='waiter', email='waiter@example.com')
    waiter.set_password('pw123456')
    db.session.add(waiter)
    db.session.commit()
    db.session.add(Reservation(
        user_id=waiter.id, book_id=book.id,
        expiration_date=datetime.utcnow() + timedelta(days=3),
    ))
    db.session.commit()

    assert loan.can_renew is False
    assert 'waiting' in loan.renew_blocked_reason.lower()


def test_renew_extends_due_date_and_increments_count(app, db, member, book):
    loan = _active_loan(db, member, book, due_in_days=1)
    old_due = loan.due_date
    loan.renew()
    assert loan.due_date > old_due
    assert loan.renewal_count == 1
    # A fresh loan period from now, not tacked onto the old due date.
    expected = datetime.utcnow() + timedelta(days=app.config['LOAN_PERIOD_DAYS'])
    assert abs((loan.due_date - expected).total_seconds()) < 5


# ---- Route behaviour ----------------------------------------------------------

def test_renew_route_extends_loan(client, db, member, book):
    login(client, 'member', 'memberpass')
    loan = _active_loan(db, member, book, due_in_days=2)
    old_due = loan.due_date

    resp = client.post(f'/renew/{loan.id}', data={'next': 'history'},
                       follow_redirects=True)
    assert resp.status_code == 200

    db.session.refresh(loan)
    assert loan.due_date > old_due
    assert loan.renewal_count == 1
    assert b'renewed' in resp.data.lower()


def test_renew_route_rejects_overdue_loan(client, db, member, book):
    login(client, 'member', 'memberpass')
    loan = _active_loan(db, member, book, due_in_days=-1)
    old_due = loan.due_date

    resp = client.post(f'/renew/{loan.id}', follow_redirects=True)
    assert resp.status_code == 200

    db.session.refresh(loan)
    assert loan.due_date == old_due
    assert loan.renewal_count == 0


def test_renew_route_rejects_other_members_loan(client, db, member, book):
    # A second member's loan should not be renewable by the logged-in member.
    other = User(username='other', email='other@example.com')
    other.set_password('otherpass123')
    db.session.add(other)
    db.session.commit()

    loan = _active_loan(db, other, book, due_in_days=5)
    old_due = loan.due_date

    login(client, 'member', 'memberpass')
    resp = client.post(f'/renew/{loan.id}', follow_redirects=True)
    assert resp.status_code == 200

    db.session.refresh(loan)
    assert loan.due_date == old_due
    assert loan.renewal_count == 0


def test_renew_route_requires_login(client, db, member, book):
    loan = _active_loan(db, member, book)
    resp = client.post(f'/renew/{loan.id}')
    assert resp.status_code in (302, 401)
    assert loan.renewal_count == 0
