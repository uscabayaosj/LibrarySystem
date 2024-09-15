from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    category = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    available_quantity = db.Column(db.Integer, default=1)

    def is_available(self):
        return self.available_quantity > 0

    def can_reserve(self):
        return self.available_quantity == 0 and self.quantity > 0

class Borrowing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime, nullable=False)

    user = db.relationship('User', backref=db.backref('borrowings', lazy=True))
    book = db.relationship('Book', backref=db.backref('borrowings', lazy=True))

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, fulfilled, expired

    user = db.relationship('User', backref=db.backref('reservations', lazy=True))
    book = db.relationship('Book', backref=db.backref('reservations', lazy=True))

    @classmethod
    def get_active_reservation(cls, book_id):
        return cls.query.filter_by(book_id=book_id, status='active').order_by(cls.reservation_date).first()

    def fulfill(self):
        self.status = 'fulfilled'
        db.session.commit()

    def expire(self):
        self.status = 'expired'
        db.session.commit()
