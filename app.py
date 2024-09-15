from flask import Flask, render_template
from config import Config
from extensions import db, login_manager
from models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

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

    return app

app = create_app()

def recreate_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()

def create_admin_user():
    with app.app_context():
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin = User(username='admin', email='admin@example.com', is_admin=True)
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print('Admin user created')

recreate_db()
create_admin_user()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
