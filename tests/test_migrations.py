"""Tests for the migration bootstrap in app.init_db().

These exercise the three states a database can be in at deploy time. The
third one -- a database created by the pre-migrations `db.create_all()` --
is the case that would otherwise break an existing deployment, so it's the
one most worth pinning down.
"""
import sqlalchemy as sa

from alembic.migration import MigrationContext

import app as app_module
from extensions import db
from models import User, Book


def _current_revision(flask_app):
    with flask_app.app_context():
        connection = db.engine.connect()
        try:
            return MigrationContext.configure(connection).get_current_revision()
        finally:
            connection.close()


def _tables(flask_app):
    with flask_app.app_context():
        return set(sa.inspect(db.engine).get_table_names())


def test_migrations_bring_up_a_brand_new_database(tmp_path, monkeypatch):
    flask_app = _build_app(tmp_path, monkeypatch, 'fresh.db')

    app_module._apply_migrations()

    assert 'user' in _tables(flask_app)
    assert 'organization_settings' in _tables(flask_app)
    assert _current_revision(flask_app) is not None


def test_migrations_are_idempotent(tmp_path, monkeypatch):
    flask_app = _build_app(tmp_path, monkeypatch, 'twice.db')

    app_module._apply_migrations()
    first = _current_revision(flask_app)
    app_module._apply_migrations()  # a second deploy with no new migrations

    assert _current_revision(flask_app) == first


def test_legacy_create_all_database_is_stamped_not_recreated(tmp_path, monkeypatch):
    """The upgrade must not try to CREATE TABLE over tables that already
    exist, and must leave existing rows alone."""
    flask_app = _build_app(tmp_path, monkeypatch, 'legacy.db')

    # Simulate a deployment from before migrations existed.
    with flask_app.app_context():
        db.create_all()
        user = User(username='existing', email='existing@example.com', is_admin=True)
        user.set_password('pw123456')
        db.session.add(user)
        db.session.add(Book(title='Pre-existing', author='A', isbn='111',
                            quantity=1, available_quantity=1))
        db.session.commit()

    assert _current_revision(flask_app) is None  # no alembic_version yet

    app_module._apply_migrations()

    assert _current_revision(flask_app) is not None
    with flask_app.app_context():
        assert User.query.filter_by(username='existing').one().is_admin is True
        assert Book.query.filter_by(title='Pre-existing').count() == 1


def test_init_db_seeds_an_admin_only_when_none_exists(tmp_path, monkeypatch):
    flask_app = _build_app(tmp_path, monkeypatch, 'seed.db')

    app_module.init_db()
    with flask_app.app_context():
        assert User.query.filter_by(is_admin=True).count() == 1

    app_module.init_db()  # re-running a deploy must not add a second admin
    with flask_app.app_context():
        assert User.query.filter_by(is_admin=True).count() == 1


def _build_app(tmp_path, monkeypatch, filename):
    """A real app instance pointed at a throwaway SQLite file.

    init_db()/_apply_migrations() operate on the module-level `app`, so that
    module global is swapped for the duration of the test.
    """
    from config import Config

    class MigrationTestConfig(Config):
        TESTING = True
        SECRET_KEY = 'test-secret'
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{tmp_path / filename}'
        WTF_CSRF_ENABLED = False
        SESSION_COOKIE_SECURE = False

    flask_app = app_module.create_app(MigrationTestConfig)
    monkeypatch.setattr(app_module, 'app', flask_app)
    return flask_app
