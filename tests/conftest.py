import os
import pytest

os.environ.setdefault('FLASK_ENV', 'testing')

from sqlalchemy import event
from sqlalchemy.engine import Engine
from app import create_app
from config import Config
from extensions import db as _db
from models import User, Book, Borrowing, Reservation, OrganizationSettings
from datetime import datetime, timedelta


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    # Process caches must not outlive a test's database.
    OrganizationSettings.forget()
    User.cache.forget()
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(db):
    user = User(username='admin', email='admin@example.com', is_admin=True)
    user.set_password('adminpass')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def member(db):
    user = User(username='member', email='member@example.com')
    user.set_password('memberpass')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def book(db):
    b = Book(title='Test Book', author='Author', isbn='1234567890123',
             category='Fiction', quantity=1, available_quantity=1)
    db.session.add(b)
    db.session.commit()
    return b


def login(client, username, password):
    return client.post('/login', data={'username': username, 'password': password},
                       follow_redirects=True)


@pytest.fixture
def count_queries():
    """Count SQL statements issued inside the `with` block."""
    class Counter:
        n = 0

    counter = Counter()

    def listener(conn, cursor, statement, parameters, context, executemany):
        counter.n += 1

    event.listen(Engine, "before_cursor_execute", listener)
    try:
        yield counter
    finally:
        event.remove(Engine, "before_cursor_execute", listener)
