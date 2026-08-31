"""Sortable columns, undo on check-in, the work-first dashboard, and the
branding preview endpoint."""
from datetime import datetime, timedelta

import models
from localtime import to_local
from models import User, Book, Borrowing, Reservation
from tests.conftest import login

FIXED_UTC_NOW = datetime(2026, 1, 10, 1, 0, 0)


def _pin_clock(monkeypatch):
    import localtime
    monkeypatch.setattr(models, 'local_now', lambda: to_local(FIXED_UTC_NOW))
    monkeypatch.setattr(localtime, 'local_now', lambda: to_local(FIXED_UTC_NOW))


def _books(db, *titles):
    made = []
    for i, t in enumerate(titles):
        b = Book(title=t, author=f'Author {t}', isbn=f'900000000000{i}',
                 category='Fiction', quantity=2, available_quantity=2)
        db.session.add(b)
        made.append(b)
    db.session.commit()
    return made


# ---- Sorting -----------------------------------------------------------------

def _titles(resp):
    import re
    return re.findall(r'data-label="Book">([^<]*)', resp.get_data(as_text=True))


def test_books_sort_by_author_both_ways(client, db, admin):
    _books(db, 'Zulu', 'Alpha', 'Mango')
    login(client, 'admin', 'adminpass')
    asc = client.get('/admin/books?sort=author&dir=asc').get_data(as_text=True)
    desc = client.get('/admin/books?sort=author&dir=desc').get_data(as_text=True)
    assert asc.index('Author Alpha') < asc.index('Author Zulu')
    assert desc.index('Author Zulu') < desc.index('Author Alpha')


def test_an_unknown_sort_key_falls_back_instead_of_erroring(client, db, admin):
    """A librarian who edits the URL should get the default list, not a 400."""
    _books(db, 'Zulu', 'Alpha')
    login(client, 'admin', 'adminpass')
    resp = client.get('/admin/books?sort=; DROP TABLE book;--&dir=sideways')
    assert resp.status_code == 200
    assert Book.query.count() == 2


def test_sort_survives_pagination_and_search(client, db, admin):
    _books(db, 'Zulu', 'Alpha', 'Mango')
    login(client, 'admin', 'adminpass')
    body = client.get('/admin/books?sort=author&dir=desc&search=Author').get_data(as_text=True)
    # Every pagination link and every header link carries the active sort, so
    # paging or re-sorting never silently drops the view.
    assert 'sort=author' in body


def test_ledger_sorts_by_member(client, db, admin, member, book):
    other = User(username='aaafirst', email='a@example.com')
    other.set_password('x' * 8)
    db.session.add(other)
    db.session.commit()
    db.session.add_all([
        Borrowing(user_id=member.id, book_id=book.id,
                  due_date=datetime.utcnow() + timedelta(days=5), status='active'),
        Borrowing(user_id=other.id, book_id=book.id,
                  due_date=datetime.utcnow() + timedelta(days=6), status='active'),
    ])
    db.session.commit()
    login(client, 'admin', 'adminpass')
    body = client.get('/admin/borrowing-history?sort=member&dir=asc').get_data(as_text=True)
    assert body.index('aaafirst') < body.index('>member<')


def test_overdue_lane_still_defaults_to_worst_first(client, db, admin, member, monkeypatch):
    """The default must not be lost now that the column is clickable."""
    _pin_clock(monkeypatch)
    a, b = _books(db, 'Slightly Late', 'Very Late')
    db.session.add_all([
        Borrowing(user_id=member.id, book_id=a.id,
                  due_date=FIXED_UTC_NOW - timedelta(days=2), status='active'),
        Borrowing(user_id=member.id, book_id=b.id,
                  due_date=FIXED_UTC_NOW - timedelta(days=30), status='active'),
    ])
    db.session.commit()
    login(client, 'admin', 'adminpass')
    titles = _titles(client.get('/admin/borrowing-history?status=overdue'))
    assert titles[0] == 'Very Late'


# ---- Undo a check-in ---------------------------------------------------------

def test_check_in_can_be_undone(client, db, admin, member, book):
    book.available_quantity = 0
    loan = Borrowing(user_id=member.id, book_id=book.id,
                     due_date=datetime.utcnow() + timedelta(days=3), status='active')
    db.session.add(loan)
    db.session.commit()

    login(client, 'admin', 'adminpass')
    client.post(f'/admin/return-book/{loan.id}', follow_redirects=True)
    db.session.refresh(loan)
    assert loan.status == 'returned'
    assert book.available_quantity == 1

    resp = client.post(f'/admin/return-book/{loan.id}/undo', follow_redirects=True)
    assert b'back on loan' in resp.data
    db.session.refresh(loan)
    assert loan.status == 'active'
    assert loan.return_date is None
    assert book.available_quantity == 0


def test_undo_offers_itself_on_the_receipt(client, db, admin, member, book):
    loan = Borrowing(user_id=member.id, book_id=book.id,
                     due_date=datetime.utcnow() + timedelta(days=3), status='active')
    db.session.add(loan)
    db.session.commit()
    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/return-book/{loan.id}', follow_redirects=True)
    assert f'/admin/return-book/{loan.id}/undo'.encode() in resp.data


def test_undo_expires(client, db, admin, member, book):
    loan = Borrowing(user_id=member.id, book_id=book.id,
                     due_date=datetime.utcnow() + timedelta(days=3), status='active')
    db.session.add(loan)
    db.session.commit()
    loan.mark_returned()
    loan.return_date = datetime.utcnow() - timedelta(hours=2)
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/return-book/{loan.id}/undo', follow_redirects=True)
    assert b'only be undone within' in resp.data
    db.session.refresh(loan)
    assert loan.status == 'returned'


def test_undo_refuses_when_the_copy_went_out_again(client, db, admin, member, book):
    """Undo must not lend a copy the shelf does not physically have."""
    book.quantity = 1
    book.available_quantity = 0
    loan = Borrowing(user_id=member.id, book_id=book.id,
                     due_date=datetime.utcnow() + timedelta(days=3), status='active')
    db.session.add(loan)
    db.session.commit()
    loan.mark_returned()                 # shelf: 1
    book.available_quantity = 0          # someone else took it
    db.session.commit()

    login(client, 'admin', 'adminpass')
    resp = client.post(f'/admin/return-book/{loan.id}/undo', follow_redirects=True)
    assert b'does not have' in resp.data
    db.session.refresh(loan)
    assert loan.status == 'returned'


def test_a_flash_carrying_an_action_is_not_auto_dismissed(client, db, admin, member, book):
    """A six-second undo is not an undo. Asserted on the JS contract the
    template relies on."""
    js = open('static/js/app.js').read()
    assert "alert.querySelector('.alert-action')" in js
    assert js.index("alert.querySelector('.alert-action')") < js.index('setTimeout(dismiss, 6000)')


# ---- Work-first dashboard ----------------------------------------------------

def test_dashboard_leads_with_overdue_not_recent_activity(client, db, admin, member, monkeypatch):
    _pin_clock(monkeypatch)
    late, recent = _books(db, 'Late Book', 'Recent Book')
    db.session.add_all([
        Borrowing(user_id=member.id, book_id=late.id,
                  due_date=FIXED_UTC_NOW - timedelta(days=6), status='active'),
        Borrowing(user_id=member.id, book_id=recent.id,
                  due_date=FIXED_UTC_NOW + timedelta(days=13), status='active'),
    ])
    db.session.commit()
    login(client, 'admin', 'adminpass')
    body = client.get('/admin/dashboard').get_data(as_text=True)
    assert 'Needs attention' in body
    # The work lane comes before the reference lane on the page.
    assert body.index('Needs attention') < body.index('Recent activity')
    assert 'Late Book' in body


def test_dashboard_offers_check_in_from_the_overdue_lane(client, db, admin, member, monkeypatch):
    _pin_clock(monkeypatch)
    late, = _books(db, 'Late Book')
    loan = Borrowing(user_id=member.id, book_id=late.id,
                     due_date=FIXED_UTC_NOW - timedelta(days=6), status='active')
    db.session.add(loan)
    db.session.commit()
    login(client, 'admin', 'adminpass')
    body = client.get('/admin/dashboard').get_data(as_text=True)
    assert f'/admin/return-book/{loan.id}' in body


def test_dashboard_says_so_when_nothing_needs_attention(client, db, admin, monkeypatch):
    _pin_clock(monkeypatch)
    login(client, 'admin', 'adminpass')
    body = client.get('/admin/dashboard').get_data(as_text=True)
    assert 'Nothing is late or due soon' in body


# ---- Branding preview --------------------------------------------------------

def test_theme_preview_returns_generated_tokens(client, db, admin):
    login(client, 'admin', 'adminpass')
    resp = client.get('/admin/settings/theme-preview?color=%23c0303c')
    assert resp.status_code == 200
    assert '--accent' in resp.get_json()['css']


def test_theme_preview_rejects_a_junk_colour_without_erroring(client, db, admin):
    login(client, 'admin', 'adminpass')
    resp = client.get('/admin/settings/theme-preview?color=notacolour')
    assert resp.status_code == 200
    assert resp.get_json()['css'] == ''


def test_theme_preview_requires_admin(client, db, member):
    login(client, 'member', 'memberpass')
    resp = client.get('/admin/settings/theme-preview?color=%23c0303c',
                      follow_redirects=True)
    assert b'do not have permission' in resp.data
