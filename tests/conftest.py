import os
import pytest

os.environ.setdefault('FLASK_ENV', 'testing')

from app import create_app
from config import Config
from extensions import db as _db
from models import User, Book, Borrowing, Reservation
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
