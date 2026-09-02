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

    # A serverless instance outlives the connections it pools, and the other
    # end hangs up without telling it. Neon suspends an idle compute and its
    # pooler drops idle connections; Vercel then reuses the same warm instance
    # and hands a request a connection the server closed minutes ago. The
    # request has done nothing wrong and still dies with
    # `psycopg2.OperationalError: SSL connection has been closed unexpectedly`,
    # which is why the symptom is a page that 500s once after a quiet period
    # and then works fine on reload -- the failed checkout discards the dead
    # connection, so the retry gets a live one.
    #
    # pool_pre_ping spends one cheap round trip proving a connection is alive
    # before handing it out, and transparently replaces it if not. pool_recycle
    # keeps connections from reaching Neon's idle timeout to begin with, so the
    # pre-ping rarely has to do the recovering.
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 240,
    }

    # Session/cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _env_flag('SESSION_COOKIE_SECURE', ENV == 'production')

    # "Remember me" issues a separate long-lived cookie (Flask-Login's
    # remember_token) so a phone borrower checking due dates in short bursts
    # isn't logged out between visits the way a plain session cookie would.
    # Hardened the same way as the session cookie above.
    REMEMBER_COOKIE_DURATION = timedelta(days=30)

    # Web Push. Both keys unset (the default) means push is off and every
    # push code path is a silent no-op: notices still land in-app. Generate a
    # pair once per deployment with `python -m push --generate` and set all
    # three in the host's environment. The subject is what the browser push
    # services can contact if the sender misbehaves; make it real.
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
    VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', 'mailto:library@example.com')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # Hard ceiling on any request body, at the WSGI layer -- defense in depth
    # around the logo upload's own (stricter) size check in branding_images.py.
    # Kept under Vercel's 4.5 MB hard limit on serverless function request
    # bodies, so an oversized upload gets this app's own friendly error
    # instead of a platform-level rejection on hosts where that limit
    # applies; the limit itself is simply unused on hosts without it.
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024

    # Flask's default for static files is `no-cache`, which makes the browser
    # revalidate the stylesheet and script on every single navigation. This is
    # a multi-page app -- each tap on the member tab bar is a full page load --
    # so on a phone that was a render-blocking round trip per tap that returned
    # 304 and no bytes. Safe to cache hard because every static URL carries a
    # ?v= stamp derived from the file's mtime (see app.py), so a changed file
    # is a changed URL rather than a stale hit.
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(days=365)

    # Business rules
    LOAN_PERIOD_DAYS = 14
    RESERVATION_HOLD_DAYS = 3
    MAX_ACTIVE_LOANS = 5
    MAX_OVERDUE_BEFORE_BLOCK = 3
    MIN_PASSWORD_LENGTH = 6
    MAX_RENEWALS = 2
