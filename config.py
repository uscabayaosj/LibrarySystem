import os


def _env_flag(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')


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

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///library.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session/cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _env_flag('SESSION_COOKIE_SECURE', ENV == 'production')

    # Business rules
    LOAN_PERIOD_DAYS = 14
    RESERVATION_HOLD_DAYS = 3
    MAX_ACTIVE_LOANS = 5
    MAX_OVERDUE_BEFORE_BLOCK = 3
    MIN_PASSWORD_LENGTH = 6
    MAX_RENEWALS = 2
