import os
from datetime import timedelta


def _env_flag(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')


def _normalize_db_url(url):
    """Accept the `postgres://` URLs most managed-database providers hand out.

    SQLAlchemy dropped that alias and only recognises `postgresql://`, so
    pasting a provider's connection string in verbatim otherwise fails at
    startup with an unhelpful 'Can't load plugin' error. Rewriting it here
    means DATABASE_URL can be copied straight from the provider dashboard.
    """
    if url.startswith('postgres://'):
        return 'postgresql://' + url[len('postgres://'):]
    return url


class Config:
    # In production, SECRET_KEY MUST be provided so that sessions survive
    # restarts and stay consistent across multiple worker processes.
    # In development we fall back to a *stable* key (not a per-process random
    # one, which would silently invalidate sessions on every reload).
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = _env_flag('FLASK_DEBUG', False)

    if not SECRET_KEY:
        if ENV == 'production':
            raise RuntimeError(
                'SECRET_KEY environment variable must be set when '
                'FLASK_ENV=production.'
            )
        SECRET_KEY = 'dev-insecure-key-change-me'

    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get('DATABASE_URL', 'sqlite:///library.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session/cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _env_flag('SESSION_COOKIE_SECURE', ENV == 'production')

    # "Remember me" issues a separate long-lived cookie (Flask-Login's
    # remember_token) so a phone borrower checking due dates in short bursts
    # isn't logged out between visits the way a plain session cookie would.
    # Hardened the same way as the session cookie above.
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # Hard ceiling on any request body, at the WSGI layer -- defense in depth
    # around the logo upload's own (stricter) size check in logo_upload.py.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # Business rules
    LOAN_PERIOD_DAYS = 14
    RESERVATION_HOLD_DAYS = 3
    MAX_ACTIVE_LOANS = 5
    MAX_OVERDUE_BEFORE_BLOCK = 3
    MIN_PASSWORD_LENGTH = 6
    MAX_RENEWALS = 2
