"""Regression tests for the four confirmed 500s from the audit, plus the
security and data-integrity fixes."""
from datetime import datetime, timedelta

from models import User, Book, Borrowing, Reservation
from tests.conftest import login


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
    assert b'day(s) left' in resp.data


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
