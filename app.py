from datetime import datetime

from flask import Flask, render_template
from config import Config
from extensions import db, login_manager, csrf
from models import User


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)

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


def init_db():
    """Create tables and seed admin user if needed. Safe to call repeatedly."""
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            import os
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
