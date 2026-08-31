"""Desk-issued password reset, in-app notices, and desk check-out."""
from datetime import datetime, timedelta

import models
from localtime import to_local
from models import User, Book, Borrowing, Reservation, Notification
from tests.conftest import login

FIXED_UTC_NOW = datetime(2026, 1, 10, 1, 0, 0)


def _pin_clock(monkeypatch):
    import localtime
    monkeypatch.setattr(models, 'local_now', lambda: to_local(FIXED_UTC_NOW))
    monkeypatch.setattr(localtime, 'local_now', lambda: to_local(FIXED_UTC_NOW))


# ---- Password reset ----------------------------------------------------------

def test_reset_code_is_single_use(db, member):
    code = member.issue_reset_code()
    db.session.commit()
    assert member.check_reset_code(code) is True
    member.set_password('brandnewpass')
    db.session.commit()
    # set_password clears the reset, so the code cannot be replayed.
    assert member.reset_code_active is False
    assert member.check_reset_code(code) is False


def test_reset_code_expires(db, member):
    code = member.issue_reset_code()
    member.reset_expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    assert member.reset_code_active is False
    assert member.check_reset_code(code) is False


def test_reset_code_is_not_stored_in_plaintext(db, member):
    code = member.issue_reset_code()
    db.session.commit()
    assert member.reset_code_hash != code
    assert code not in (member.reset_code_hash or '')


def test_issuing_a_new_code_invalidates_the_old_one(db, member):
    first = member.issue_reset_code()
    db.session.commit()
    second = member.issue_reset_code()
    db.session.commit()
    assert member.check_reset_code(second) is True
    assert member.check_reset_code(first) is False


def test_librarian_can_issue_a_code_and_it_is_shown_once(client, db, admin, member):
    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/members/{member.id}/reset-password', follow_redirects=True)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'One-time code for member' in body
    db.session.refresh(member)
    assert member.reset_code_active is True
    # The page rendered after the flash is consumed must not repeat the code.
    again = client.get(f'/admin/members/{member.id}').get_data(as_text=True)
    assert 'One-time code' not in again


def test_admin_passwords_cannot_be_reset_from_the_ui(client, db, admin):
    """The seeded admin is provisioned by the deployment. Letting the UI reset
    it would make it recoverable by anyone who reaches this page."""
    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/members/{admin.id}/reset-password', follow_redirects=True)
    assert b'set through the deployment' in resp.data
    db.session.refresh(admin)
    assert admin.reset_code_active is False


def test_member_redeems_a_code_and_can_sign_in_with_the_new_password(client, db, member):
    code = member.issue_reset_code()
    db.session.commit()
    resp = client.post('/reset', data={
        'username': 'member', 'code': code,
        'password': 'chosenbyme', 'confirm': 'chosenbyme',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'You can sign in with it now' in resp.data
    signed_in = login(client, 'member', 'chosenbyme')
    assert signed_in.status_code == 200
    db.session.refresh(member)
    assert member.reset_code_active is False


def test_a_wrong_code_and_an_unknown_user_are_indistinguishable(client, db, member):
    """Otherwise the form is a username oracle."""
    member.issue_reset_code()
    db.session.commit()
    wrong = client.post('/reset', data={
        'username': 'member', 'code': 'WRONGWRONG',
        'password': 'chosenbyme', 'confirm': 'chosenbyme'}).get_data(as_text=True)
    nobody = client.post('/reset', data={
        'username': 'nosuchperson', 'code': 'WRONGWRONG',
        'password': 'chosenbyme', 'confirm': 'chosenbyme'}).get_data(as_text=True)
    # Jinja escapes the apostrophe, so match on the unambiguous tail.
    assert 'valid, or it has expired' in wrong
    assert 'valid, or it has expired' in nobody
    # And the two responses say the same thing, which is the actual property
    # under test -- not merely that each says something.
    assert ('valid, or it has expired' in wrong) == ('valid, or it has expired' in nobody)


def test_reset_rejects_mismatched_confirmation(client, db, member):
    code = member.issue_reset_code()
    db.session.commit()
    resp = client.post('/reset', data={
        'username': 'member', 'code': code,
        'password': 'chosenbyme', 'confirm': 'somethingelse'})
    assert b"don&#39;t match" in resp.data or b"don't match" in resp.data
    assert member.check_password('memberpass')


def test_login_offers_the_reset_route(client, db):
    assert b'Forgot password?' in client.get('/login').data


# ---- Notices -----------------------------------------------------------------

def test_sweep_raises_one_notice_per_loan_state(db, member, book, monkeypatch):
    _pin_clock(monkeypatch)
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=FIXED_UTC_NOW - timedelta(days=9), status='active'))
    db.session.commit()
    assert Notification.sweep_loans() == 1
    db.session.commit()
    note = Notification.query.one()
    assert note.kind == 'overdue'
    assert book.title in note.title


def test_sweep_is_idempotent(db, member, book, monkeypatch):
    """The librarian presses this button whenever they like; a member must not
    collect a fresh copy of the same notice every time."""
    _pin_clock(monkeypatch)
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=FIXED_UTC_NOW + timedelta(days=2), status='active'))
    db.session.commit()
    assert Notification.sweep_loans() == 1
    db.session.commit()
    for _ in range(4):
        assert Notification.sweep_loans() == 0
        db.session.commit()
    assert Notification.query.count() == 1


def test_a_loan_crossing_from_due_soon_to_overdue_gets_both_notices(db, member, book, monkeypatch):
    _pin_clock(monkeypatch)
    loan = Borrowing(user_id=member.id, book_id=book.id,
                     due_date=FIXED_UTC_NOW + timedelta(days=2), status='active')
    db.session.add(loan)
    db.session.commit()
    Notification.sweep_loans()
    db.session.commit()
    loan.due_date = FIXED_UTC_NOW - timedelta(days=3)
    db.session.commit()
    Notification.sweep_loans()
    db.session.commit()
    assert {n.kind for n in Notification.query.all()} == {'due_soon', 'overdue'}


def test_healthy_loans_raise_nothing(db, member, book, monkeypatch):
    _pin_clock(monkeypatch)
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=FIXED_UTC_NOW + timedelta(days=11), status='active'))
    db.session.commit()
    assert Notification.sweep_loans() == 0


def test_fulfilling_a_hold_notifies_the_member(client, db, admin, member, book):
    """The moment the queue exists to produce. It used to reach the member only
    if they happened to notice a card had changed."""
    book.available_quantity = 1
    db.session.add(Reservation(user_id=member.id, book_id=book.id,
                               expiration_date=datetime.utcnow() + timedelta(days=3)))
    db.session.commit()
    login(client, 'admin', 'adminpass')
    client.post('/admin/check-reservations', follow_redirects=True)
    ready = Notification.query.filter_by(kind='hold_ready').one()
    assert ready.user_id == member.id
    assert book.title in ready.title


def test_member_sees_and_can_clear_unread_notices(client, db, member, book, monkeypatch):
    _pin_clock(monkeypatch)
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=FIXED_UTC_NOW - timedelta(days=4), status='active'))
    db.session.commit()
    Notification.sweep_loans()
    db.session.commit()

    login(client, 'member', 'memberpass')
    assert Notification.unread_count(member.id) == 1
    listing = client.get('/notifications')
    assert listing.status_code == 200
    assert b'is overdue' in listing.data

    client.post('/notifications/read', follow_redirects=True)
    assert Notification.unread_count(member.id) == 0


def test_notices_are_scoped_to_their_owner(client, db, member, book, monkeypatch):
    _pin_clock(monkeypatch)
    other = User(username='someoneelse', email='other@example.com')
    other.set_password('otherpass')
    db.session.add(other)
    db.session.commit()
    db.session.add(Borrowing(user_id=other.id, book_id=book.id,
                             due_date=FIXED_UTC_NOW - timedelta(days=4), status='active'))
    db.session.commit()
    Notification.sweep_loans()
    db.session.commit()

    login(client, 'member', 'memberpass')
    # Assert on the record, not on a substring: the empty-state copy legitimately
    # contains the phrase "is overdue" while explaining what notices are for.
    assert Notification.query.filter_by(user_id=member.id).count() == 0
    assert Notification.unread_count(member.id) == 0
    page = client.get('/notifications').get_data(as_text=True)
    assert 'No notices yet' in page
    assert book.title not in page


# ---- Desk check-out ----------------------------------------------------------

def test_librarian_can_check_a_book_out(client, db, admin, member, book):
    login(client, 'admin', 'adminpass')
    before = book.available_quantity
    resp = client.post('/admin/checkout', data={
        'member_id': member.id, 'book_id': book.id}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'checked out to member' in resp.data
    loan = Borrowing.query.filter_by(user_id=member.id, book_id=book.id,
                                     status='active').one()
    assert loan.due_date is not None
    assert book.available_quantity == before - 1
    # And the member is told, without having to notice a row appear.
    assert Notification.query.filter_by(kind='checked_out').count() == 1


def test_checkout_enforces_the_same_block_the_member_sees(client, db, admin, member, book, monkeypatch):
    """No silent librarian override: this app has no audit trail, so bypassing
    a limit invisibly would leave nobody accountable for it."""
    _pin_clock(monkeypatch)
    for i in range(3):
        late = Book(title=f'Late {i}', author='A', isbn=f'99900000000{i}',
                    quantity=1, available_quantity=0)
        db.session.add(late)
        db.session.flush()
        db.session.add(Borrowing(user_id=member.id, book_id=late.id,
                                 due_date=FIXED_UTC_NOW - timedelta(days=5),
                                 status='active'))
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/checkout', data={
        'member_id': member.id, 'book_id': book.id}, follow_redirects=True)
    assert b'blocking new loans' in resp.data
    assert Borrowing.query.filter_by(book_id=book.id, status='active').count() == 0


def test_checkout_will_not_jump_someone_elses_queue(client, db, admin, member, book):
    waiting = User(username='waiting', email='waiting@example.com')
    waiting.set_password('waitingpass')
    db.session.add(waiting)
    db.session.commit()
    db.session.add(Reservation(user_id=waiting.id, book_id=book.id,
                               expiration_date=datetime.utcnow() + timedelta(days=3)))
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/checkout', data={
        'member_id': member.id, 'book_id': book.id}, follow_redirects=True)
    assert b'who is next in line' in resp.data
    assert Borrowing.query.filter_by(user_id=member.id, status='active').count() == 0


def test_checkout_to_the_member_at_the_front_consumes_their_hold(client, db, admin, member, book):
    """Otherwise the hold stays active against a copy they are now carrying."""
    hold = Reservation(user_id=member.id, book_id=book.id,
                       expiration_date=datetime.utcnow() + timedelta(days=3))
    db.session.add(hold)
    db.session.commit()

    login(client, 'admin', 'adminpass')
    client.post('/admin/checkout', data={
        'member_id': member.id, 'book_id': book.id}, follow_redirects=True)
    db.session.refresh(hold)
    assert hold.status == 'fulfilled'
    assert Borrowing.query.filter_by(user_id=member.id, book_id=book.id,
                                     status='active').count() == 1


def test_checkout_refuses_a_second_copy_of_a_title_already_held(client, db, admin, member, book):
    book.quantity = 2
    book.available_quantity = 2
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=datetime.utcnow() + timedelta(days=14),
                             status='active'))
    db.session.commit()
    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/checkout', data={
        'member_id': member.id, 'book_id': book.id}, follow_redirects=True)
    assert b'already has a copy' in resp.data
    assert Borrowing.query.filter_by(user_id=member.id, status='active').count() == 1


def test_checkout_refuses_when_no_copies_are_on_the_shelf(client, db, admin, member, book):
    book.available_quantity = 0
    db.session.commit()
    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/checkout', data={
        'member_id': member.id, 'book_id': book.id}, follow_redirects=True)
    assert b'No copies are on the shelf' in resp.data
    assert Borrowing.query.filter_by(status='active').count() == 0


def test_checkout_page_requires_admin(client, db, member):
    login(client, 'member', 'memberpass')
    resp = client.get('/admin/checkout', follow_redirects=True)
    assert b'do not have permission' in resp.data


def test_due_soon_notice_reads_as_a_sentence(db, member, book, monkeypatch):
    """due_label is written to stand alone in a badge ("2 days left"); dropped
    into a sentence frame it produced '"X" is 2 days left'."""
    _pin_clock(monkeypatch)
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=FIXED_UTC_NOW + timedelta(days=2), status='active'))
    db.session.commit()
    Notification.sweep_loans()
    db.session.commit()
    assert Notification.query.one().title == f'"{book.title}" is due in 2 days'


def test_due_today_and_tomorrow_read_naturally(db, member, monkeypatch):
    _pin_clock(monkeypatch)
    today_book = Book(title='Due Today', author='A', isbn='1110000000001',
                      quantity=1, available_quantity=1)
    tomorrow_book = Book(title='Due Tomorrow', author='A', isbn='1110000000002',
                         quantity=1, available_quantity=1)
    db.session.add_all([today_book, tomorrow_book])
    db.session.commit()
    db.session.add_all([
        Borrowing(user_id=member.id, book_id=today_book.id,
                  due_date=FIXED_UTC_NOW - timedelta(hours=2), status='active'),
        Borrowing(user_id=member.id, book_id=tomorrow_book.id,
                  due_date=FIXED_UTC_NOW + timedelta(days=1), status='active'),
    ])
    db.session.commit()
    Notification.sweep_loans()
    db.session.commit()
    titles = {n.title for n in Notification.query.all()}
    assert '"Due Today" is due today' in titles
    assert '"Due Tomorrow" is due tomorrow' in titles
