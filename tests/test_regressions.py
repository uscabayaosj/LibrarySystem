"""Regression tests for the four confirmed 500s from the audit, plus the
security and data-integrity fixes."""
from datetime import datetime, timedelta, timezone

import models
from localtime import to_local, local_now
from models import User, Book, Borrowing, Reservation
from tests.conftest import login

# A fixed instant, deliberately mid-morning in the library's local timezone
# (see localtime.py) so it sits nowhere near a day boundary in either UTC or
# local time. Calendar-day math (days_until_due, days_until_expiry) depends
# on *when* "now" is, not just the elapsed offset -- a due_date built as
# "utcnow() + 1 day 2 hours" crosses a different number of local-midnight
# boundaries depending on the wall-clock time the test happens to run at.
# Pinning models.local_now() to this instant makes those tests deterministic
# regardless of when CI runs them.
FIXED_UTC_NOW = datetime(2026, 1, 10, 1, 0, 0)


# ---- §1.1: My Reservations page no longer 500s -------------------------------

def test_reservations_page_renders_with_active_reservation(client, db, member, book):
    book.available_quantity = 0
    r = Reservation(user_id=member.id, book_id=book.id,
                    expiration_date=datetime.utcnow() + timedelta(days=3))
    db.session.add(r)
    db.session.commit()

    login(client, 'member', 'memberpass')
    resp = client.get('/reservations')
    assert resp.status_code == 200
    assert book.title.encode() in resp.data
    # A reservation with days to spare shows the calm hold-deadline form
    # ("Held until <date>") rather than an alarm countdown -- the countdown
    # only appears in the last day, so an in-line member isn't told they're
    # about to lose a hold they were never offered.
    assert b'Held until' in resp.data


# ---- §1.2 / §1.3: deleting records with history no longer 500s ---------------

def test_delete_book_with_returned_history(client, db, admin, member, book):
    b = Borrowing(user_id=member.id, book_id=book.id,
                  due_date=datetime.utcnow() + timedelta(days=14),
                  status='returned', return_date=datetime.utcnow())
    db.session.add(b)
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/books/{book.id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    assert Book.query.get(book.id) is None
    assert Borrowing.query.count() == 0  # cascade removed history


def test_delete_member_with_history(client, db, admin, member, book):
    b = Borrowing(user_id=member.id, book_id=book.id,
                  due_date=datetime.utcnow() + timedelta(days=14),
                  status='returned', return_date=datetime.utcnow())
    db.session.add(b)
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/members/{member.id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    assert User.query.get(member.id) is None


def test_cannot_delete_book_with_active_loan(client, db, admin, member, book):
    b = Borrowing(user_id=member.id, book_id=book.id,
                  due_date=datetime.utcnow() + timedelta(days=14), status='active')
    db.session.add(b)
    db.session.commit()

    login(client, 'admin', 'adminpass')
    client.post(f'/admin/books/{book.id}/delete', follow_redirects=True)
    assert Book.query.get(book.id) is not None  # blocked, still present


# ---- §1.4: editing to a duplicate ISBN is handled gracefully -----------------

def test_edit_book_duplicate_isbn(client, db, admin):
    b1 = Book(title='B1', author='A', isbn='111', quantity=1, available_quantity=1)
    b2 = Book(title='B2', author='A', isbn='222', quantity=1, available_quantity=1)
    db.session.add_all([b1, b2])
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/books/{b2.id}/edit',
                       data={'title': 'B2', 'author': 'A', 'isbn': '111', 'quantity': '1'},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert Book.query.get(b2.id).isbn == '222'  # unchanged


# ---- UI/UX §1: due-date arithmetic is self-consistent ------------------------

def test_due_labels_agree_in_both_directions(db, member, book):
    """The old code subtracted timestamps in opposite orders in different
    templates, so one loan rendered as both '7 days overdue' and '8 days
    overdue'. Every label now derives from one calendar-date property."""
    # Anchored in the library's own timezone, not UTC. days_until_due compares
    # *local calendar dates*, so a UTC-relative "7 days and 6 hours ago" lands
    # 7 or 8 local days back depending on the hour the suite happens to run --
    # it failed for 6 of every 24 UTC hours. Building the date in local time
    # and placing it at local midday keeps it clear of either boundary.
    local_due = (local_now() - timedelta(days=7)).replace(hour=12, minute=0,
                                                          second=0, microsecond=0)
    b = Borrowing(user_id=member.id, book_id=book.id,
                  due_date=local_due.astimezone(timezone.utc).replace(tzinfo=None),
                  status='active')
    db.session.add(b)
    db.session.commit()

    assert b.days_until_due == -7
    assert b.days_overdue == 7
    assert b.due_state == 'overdue'
    assert b.due_label == '7 days overdue'


def test_due_today_is_not_reported_as_overdue_zero(db, member, book, monkeypatch):
    """A book due earlier today used to render '0 day(s) overdue'.

    Pinned to FIXED_UTC_NOW like its neighbours. Built from utcnow() this was
    flaky on a daily schedule: the property compares *local* calendar days, so
    whenever local midnight fell inside the two-hour window the fixture spans,
    'earlier today' became yesterday and the count came out -1.

    The offset also does real work here. FIXED_UTC_NOW is 09:00 local, so two
    hours earlier is 07:00 local the same day but 23:00 UTC the *previous* day
    -- the exact divergence days_until_due exists to get right.
    """
    monkeypatch.setattr(models, 'local_now', lambda: to_local(FIXED_UTC_NOW))
    b = Borrowing(user_id=member.id, book_id=book.id,
                  due_date=FIXED_UTC_NOW - timedelta(hours=2), status='active')
    db.session.add(b)
    db.session.commit()

    assert b.days_until_due == 0
    assert b.due_state == 'today'
    assert b.due_label == 'Due today'


def test_days_left_is_not_short_by_one(db, member, book, monkeypatch):
    """A book due in 1d18h used to read '1 day(s) left'; by calendar date it
    is due the day after tomorrow, i.e. 2 days."""
    monkeypatch.setattr(models, 'local_now', lambda: to_local(FIXED_UTC_NOW))
    b = Borrowing(user_id=member.id, book_id=book.id,
                  due_date=FIXED_UTC_NOW + timedelta(days=1, hours=18), status='active')
    db.session.add(b)
    db.session.commit()

    assert b.days_until_due == 2
    assert b.due_label == '2 days left'


def test_singular_day_is_not_pluralised(db, member, book, monkeypatch):
    monkeypatch.setattr(models, 'local_now', lambda: to_local(FIXED_UTC_NOW))
    b = Borrowing(user_id=member.id, book_id=book.id,
                  due_date=FIXED_UTC_NOW + timedelta(days=1, hours=2),
                  status='active')
    db.session.add(b)
    db.session.commit()
    assert b.due_label == '1 day left'


# ---- UI/UX §5: the overdue filter actually filters to overdue ---------------

def test_overdue_filter_excludes_on_time_loans(client, db, admin, member, book):
    now = datetime.utcnow()
    other = Book(title='On Time', author='A', isbn='555', quantity=1, available_quantity=1)
    db.session.add(other)
    db.session.commit()
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=now - timedelta(days=3), status='active'))
    db.session.add(Borrowing(user_id=member.id, book_id=other.id,
                             due_date=now + timedelta(days=10), status='active'))
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.get('/admin/borrowing-history?status=overdue')
    assert resp.status_code == 200
    assert book.title.encode() in resp.data
    assert b'On Time' not in resp.data


# ---- §2.2: no duplicate active borrowing of the same title -------------------

def test_cannot_borrow_same_book_twice(client, db, member):
    book = Book(title='Dup', author='A', isbn='999', quantity=5, available_quantity=5)
    db.session.add(book)
    db.session.commit()

    login(client, 'member', 'memberpass')
    client.post(f'/borrow/{book.id}', follow_redirects=True)
    client.post(f'/borrow/{book.id}', follow_redirects=True)
    active = Borrowing.query.filter_by(user_id=member.id, book_id=book.id,
                                       status='active').count()
    assert active == 1


# ---- §2.1: availability cannot go negative -----------------------------------

def test_borrow_last_copy_then_unavailable(client, db, member, book):
    login(client, 'member', 'memberpass')
    client.post(f'/borrow/{book.id}', follow_redirects=True)
    db.session.refresh(book)
    assert book.available_quantity == 0


# ---- §3.3: open-redirect protection ------------------------------------------

def test_login_rejects_external_next(client, admin):
    resp = client.post('/login?next=https://evil.com',
                       data={'username': 'admin', 'password': 'adminpass'})
    assert 'evil.com' not in resp.headers.get('Location', '')


def test_login_rejects_scheme_relative_next(client, admin):
    resp = client.post('/login?next=//evil.com',
                       data={'username': 'admin', 'password': 'adminpass'})
    assert 'evil.com' not in resp.headers.get('Location', '')


# ---- §3.2: CSRF protection is active in a non-testing config ------------------

def test_csrf_blocks_tokenless_post(db, member):
    from app import create_app
    from config import Config

    class CsrfConfig(Config):
        TESTING = True
        SECRET_KEY = 'x'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfConfig)
    with app.app_context():
        db.create_all()
        u = User(username='m2', email='m2@e.com')
        u.set_password('pw12345')
        db.session.add(u)
        db.session.commit()
        c = app.test_client()
        c.post('/login', data={'username': 'm2', 'password': 'pw12345'})
        resp = c.post('/borrow/1')
        assert resp.status_code == 400  # missing CSRF token rejected
        db.drop_all()


# ---- §3.4: password length enforced ------------------------------------------

def test_register_rejects_short_password(client, db):
    resp = client.post('/register',
                       data={'username': 'newuser', 'email': 'n@e.com', 'password': 'ab'},
                       follow_redirects=True)
    assert User.query.filter_by(username='newuser').first() is None
    assert b'at least' in resp.data


def test_register_normalizes_email(client, db):
    client.post('/register',
                data={'username': 'caseuser', 'email': 'MixedCase@Example.com',
                      'password': 'secret1'},
                follow_redirects=True)
    user = User.query.filter_by(username='caseuser').first()
    assert user is not None
    assert user.email == 'mixedcase@example.com'
