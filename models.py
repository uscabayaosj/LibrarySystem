from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def active_borrowings(self):
        return Borrowing.query.filter_by(user_id=self.id, status='active').count()

    @property
    def overdue_borrowings(self):
        return Borrowing.query.filter(
            Borrowing.user_id == self.id,
            Borrowing.status == 'active',
            Borrowing.due_date < datetime.utcnow()
        ).count()

    @property
    def active_reservations_count(self):
        return Reservation.query.filter_by(user_id=self.id, status='active').count()


class Book(db.Model):
    __tablename__ = 'book'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(100), nullable=False, index=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), index=True)
    publisher = db.Column(db.String(100))
    publication_year = db.Column(db.Integer)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=1)
    available_quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_available(self):
        return self.available_quantity > 0

    def can_reserve(self):
        return self.available_quantity == 0 and self.quantity > 0


class Borrowing(db.Model):
    __tablename__ = 'borrowing'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False, index=True)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, returned, overdue

    user = db.relationship('User', backref=db.backref('borrowings', lazy='dynamic'))
    book = db.relationship('Book', backref=db.backref('borrowings', lazy='dynamic'))

    @property
    def is_overdue(self):
        return self.status == 'active' and self.due_date < datetime.utcnow()

    @property
    def days_until_due(self):
        if self.status != 'active':
            return None
        delta = (self.due_date - datetime.utcnow()).days
        return delta

    def mark_returned(self):
        self.status = 'returned'
        self.return_date = datetime.utcnow()
        self.book.available_quantity += 1
        db.session.commit()


class Reservation(db.Model):
    __tablename__ = 'reservation'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False, index=True)
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active', index=True)  # active, fulfilled, expired, cancelled

    user = db.relationship('User', backref=db.backref('reservations', lazy='dynamic'))
    book = db.relationship('Book', backref=db.backref('reservations', lazy='dynamic'))

    @classmethod
    def get_active_reservation(cls, book_id):
        return cls.query.filter_by(book_id=book_id, status='active').order_by(cls.reservation_date).first()

    def fulfill(self):
        self.status = 'fulfilled'
        db.session.commit()

    def expire(self):
        self.status = 'expired'
        db.session.commit()
