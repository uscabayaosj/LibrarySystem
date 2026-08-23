"""Tests for the migration bootstrap in app.init_db().

These exercise the three states a database can be in at deploy time. The
third one -- a database created by the pre-migrations `db.create_all()` --
is the case that would otherwise break an existing deployment, so it's the
one most worth pinning down.
"""
from datetime import datetime

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

    # Simulate a deployment from before migrations existed: build the schema
    # by actually running the baseline migration (never db.create_all() --
    # that reflects whatever models.py declares *right now*, which drifts
    # from the baseline the instant a second migration adds a column, and
    # would make this "legacy" fixture silently describe the current schema
    # instead of the historical one), then drop alembic_version -- a
    # pre-Alembic install never had that table to begin with.
    from flask_migrate import upgrade as migrate_upgrade
    with flask_app.app_context():
        migrate_upgrade(revision=app_module._BASELINE_REVISION)
        db.session.execute(sa.text('DROP TABLE alembic_version'))
        db.session.commit()

        # Raw SQL, not the User ORM model: the model now carries columns
        # (onboarding_completed_at) added by a migration after baseline, so
        # inserting through it here -- against a table genuinely stamped at
        # baseline -- would fail with "no such column", the same drift this
        # fixture already guards the schema-creation step against above.
        user = User(username='existing', email='existing@example.com', is_admin=True)
        user.set_password('pw123456')
        db.session.execute(sa.text(
            'INSERT INTO user (username, email, password_hash, is_admin, phone, member_since) '
            'VALUES (:username, :email, :password_hash, :is_admin, NULL, :member_since)'
        ), {
            'username': user.username, 'email': user.email,
            'password_hash': user.password_hash, 'is_admin': True,
            'member_since': datetime.utcnow(),
        })
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


# ---- Deploy-safety guards --------------------------------------------------

def test_seed_does_not_print_the_admin_password(tmp_path, monkeypatch, capsys):
    """The seed message must never echo ADMIN_PASSWORD -- init_db() runs on
    every boot, and host deploy logs are long-lived and widely readable."""
    _build_app(tmp_path, monkeypatch, 'nopw.db')
    monkeypatch.setenv('ADMIN_PASSWORD', 'sup3r-s3cret-value')

    app_module.init_db()

    out = capsys.readouterr().out
    assert 'sup3r-s3cret-value' not in out
    assert 'admin' in out.lower()


def test_default_admin_password_is_called_out(tmp_path, monkeypatch, capsys):
    """With no ADMIN_PASSWORD set the account really is admin/admin, so that
    case should say so loudly rather than being coy about it."""
    _build_app(tmp_path, monkeypatch, 'defaultpw.db')
    monkeypatch.delenv('ADMIN_PASSWORD', raising=False)

    app_module.init_db()

    out = capsys.readouterr().out
    assert 'CHANGE THIS PASSWORD' in out


def test_production_on_sqlite_warns_loudly(tmp_path, monkeypatch, capsys):
    flask_app = _build_app(tmp_path, monkeypatch, 'warn.db')
    flask_app.config['ENV'] = 'production'

    app_module._warn_if_ephemeral_database()

    out = capsys.readouterr().out
    assert 'WARNING' in out
    assert 'DATABASE_URL' in out
    assert 'DESTROYED ON THE NEXT DEPLOY' in out


def test_no_warning_outside_production_or_on_postgres(tmp_path, monkeypatch, capsys):
    flask_app = _build_app(tmp_path, monkeypatch, 'nowarn.db')

    # Development on SQLite is the normal local setup -- no warning.
    flask_app.config['ENV'] = 'development'
    app_module._warn_if_ephemeral_database()
    assert 'WARNING' not in capsys.readouterr().out

    # Production on Postgres is the intended production setup -- no warning.
    flask_app.config['ENV'] = 'production'
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user@host/db'
    app_module._warn_if_ephemeral_database()
    assert 'WARNING' not in capsys.readouterr().out
