import hashlib
import os
from datetime import datetime

import sqlalchemy as sa
from flask import Flask, render_template, jsonify, url_for
from config import Config
from extensions import db, login_manager, csrf, migrate
from models import User, OrganizationSettings
from theming import build_theme_css


def cover_hue(seed):
    """A stable hue (0-359) derived from a book's ISBN (or any string), so
    every book gets a consistent 'cover' colour across requests and process
    restarts -- unlike Python's built-in hash(), which is randomised per
    process and would make covers flicker to a different colour on every
    server restart."""
    digest = hashlib.md5(str(seed or '').encode('utf-8')).hexdigest()
    return int(digest, 16) % 360


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    # render_as_batch lets Alembic emit ALTER TABLE for SQLite, which doesn't
    # support most ALTERs natively -- without it, any future column change
    # would generate a migration that works on Postgres and fails on SQLite.
    migrate.init_app(app, db, render_as_batch=True)

    app.add_template_filter(cover_hue)

    with app.app_context():
        from routes import auth, admin, member
        app.register_blueprint(auth.bp)
        app.register_blueprint(admin.bp)
        app.register_blueprint(member.bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_now():
        # Makes `now` available to every template so due/overdue math and
        # date displays don't depend on each route remembering to pass it.
        return {'now': datetime.utcnow()}

    @app.context_processor
    def inject_org_branding():
        # Per-deployment branding (org name / logo / theme color), available
        # on every page including the public/unauthenticated ones.
        settings = OrganizationSettings.get()
        theme_css = build_theme_css(settings.theme_color) if settings.theme_color else ''
        return {'org_settings': settings, 'org_theme_css': theme_css}

    @app.route('/manifest.json')
    def manifest():
        # Generated per-request (cheap: one row lookup) rather than a static
        # file, so the installed-app name and icon follow whatever the admin
        # has set in Settings -- an org that uploads its own logo gets its
        # own home-screen icon, not the library's default book mark.
        settings = OrganizationSettings.get()
        icon_dir = 'uploads/branding' if settings.logo_filename else 'icons'
        icons = [
            {'src': url_for('static', filename=f'{icon_dir}/icon-192.png'),
             'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': url_for('static', filename=f'{icon_dir}/icon-512.png'),
             'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': url_for('static', filename=f'{icon_dir}/icon-192-maskable.png'),
             'sizes': '192x192', 'type': 'image/png', 'purpose': 'maskable'},
            {'src': url_for('static', filename=f'{icon_dir}/icon-512-maskable.png'),
             'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ]
        manifest_data = {
            'name': settings.org_name,
            'short_name': settings.org_name[:12] or 'Library',
            'description': f'Browse, borrow, and reserve from the {settings.org_name} collection.',
            'start_url': '/dashboard',
            'scope': '/',
            'display': 'standalone',
            'orientation': 'portrait-primary',
            'background_color': '#E8E8EA',
            'theme_color': settings.theme_color or '#0069D9',
            'icons': icons,
        }
        response = jsonify(manifest_data)
        response.headers['Content-Type'] = 'application/manifest+json'
        return response

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app


app = create_app()


def _apply_migrations():
    """Bring the database up to the latest migration.

    Three cases have to work, because a deploy shouldn't need anyone to think
    about which one they're in:

    1. Brand-new database -> run every migration from scratch.
    2. Database already managed by Alembic -> apply whatever is outstanding.
    3. Database created by the pre-migrations `db.create_all()` (it has the
       tables but no alembic_version row) -> stamp it at the initial revision
       first, so Alembic doesn't try to CREATE TABLE over tables that already
       exist, then apply anything newer.
    """
    from alembic.migration import MigrationContext
    from flask_migrate import stamp, upgrade

    with app.app_context():
        connection = db.engine.connect()
        try:
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()
            inspector = sa.inspect(db.engine)
            has_legacy_tables = inspector.has_table('user')
        finally:
            connection.close()

        if current_revision is None and has_legacy_tables:
            # Case 3: pre-existing schema from create_all(). _BASELINE_REVISION
            # is the revision whose upgrade() produces exactly that schema.
            stamp(revision=_BASELINE_REVISION)
            print(f'Existing database stamped at {_BASELINE_REVISION}.')

        upgrade()


# The initial migration -- the schema an old create_all() database already has.
_BASELINE_REVISION = 'a062ad0fb313'


def init_db():
    """Migrate to the latest schema and seed an admin user if there isn't one.
    Safe to call repeatedly, and safe to call on every boot."""
    _apply_migrations()
    with app.app_context():
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            seed_password = os.environ.get('ADMIN_PASSWORD', 'admin')
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password(seed_password)
            db.session.add(admin)
            db.session.commit()
            print(f'Admin user created (admin / {seed_password})')


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
