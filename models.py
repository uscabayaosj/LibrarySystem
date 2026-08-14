from flask import current_app, g, has_app_context
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import cached_property
from sqlalchemy import event
from extensions import db
from localtime import to_local, local_now

# Several display properties below issue their own query (a reservation
# lookup, a count). Templates read them more than once per object -- the
# dashboard alone asked for renew_blocked_reason three times per loan, via
# can_renew, then the elif, then the output -- which turned five loans into
# fifteen identical SELECTs. They are memoized with cached_property, which
# is safe because SQLAlchemy hands out a fresh instance per request and the
# session is torn down at the end of it, so a cached value never outlives
# the request that computed it. Mutating methods clear their own entries so
# a read-after-write inside one request still sees the truth.


class OrganizationSettings(db.Model):
    """Singleton row (always id=1) holding the per-deployment branding: the
    organization's display name, an optional uploaded logo, and a custom
    theme color. A real table (rather than a config file) so an admin can
    change branding from the UI without redeploying or touching the
    environment."""
    __tablename__ = 'organization_settings'

    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(80), nullable=False, default='Library System')
    logo_filename = db.Column(db.String(120))
    theme_color = db.Column(db.String(7))  # '#rrggbb', or None for the default palette

    @classmethod
    def get(cls):
        """Fetch the singleton row, creating it with defaults on first use."""
        settings = cls.query.get(1)
        if settings is None:
            settings = cls(id=1)
            db.session.add(settings)
            db.session.commit()
        return settings


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

    # Read on every page: the member tab bar renders unread-style badges from
    # these, and the dashboard reads them again for its summary tiles.
    @cached_property
    def active_borrowings(self):
        return Borrowing.query.filter_by(user_id=self.id, status='active').count()

    @cached_property
    def overdue_borrowings(self):
        return Borrowing.query.filter(
            Borrowing.user_id == self.id,
            Borrowing.status == 'active',
            Borrowing.due_date < datetime.utcnow()
        ).count()

    @cached_property
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
    renewal_count = db.Column(db.Integer, default=0, nullable=False)

    user = db.relationship('User', backref=db.backref(
        'borrowings', lazy='dynamic', cascade='all, delete-orphan'))
    book = db.relationship('Book', backref=db.backref(
        'borrowings', lazy='dynamic', cascade='all, delete-orphan'))

    @property
    def is_overdue(self):
        return self.status == 'active' and self.due_date < datetime.utcnow()

    @property
    def days_until_due(self):
        """Whole days until the due date: positive = time remains, 0 = due
        today, negative = overdue.

        Compared on calendar dates rather than timestamps. Due dates are
        day-granular to a borrower, so the time-of-day component must not
        influence the count -- and subtracting timestamps in the two possible
        orders gives answers that differ by one, because timedelta.days floors
        toward negative infinity. Deriving every label from this one property
        keeps those numbers consistent everywhere they are shown.

        The comparison happens in the library's local timezone (see
        localtime.py), not the server's UTC clock -- otherwise "today" flips
        over at UTC midnight, which is mid-morning for every actual user of
        this deployment, and a book due-today could read as due-tomorrow (or
        vice versa) for hours at a stretch.
        """
        if self.due_date is None:
            return None
        return (to_local(self.due_date).date() - local_now().date()).days

    @property
    def days_overdue(self):
        """Whole days past the due date; 0 when not overdue."""
        days = self.days_until_due
        if days is None or days >= 0:
            return 0
        return -days

    @property
    def due_state(self):
        """Single label driving colour and copy: returned | overdue | today |
        soon | ok."""
        if self.status == 'returned':
            return 'returned'
        days = self.days_until_due
        if days is None:
            return 'ok'
        if days < 0:
            return 'overdue'
        if days == 0:
            return 'today'
        if days <= 3:
            return 'soon'
        return 'ok'

    @property
    def due_label(self):
        """Human phrasing of due_state, e.g. '3 days left', 'Due today'."""
        state = self.due_state
        if state == 'returned':
            return 'Returned'
        days = self.days_until_due
        if state == 'overdue':
            n = -days
            return f"{n} day{'s' if n != 1 else ''} overdue"
        if state == 'today':
            return 'Due today'
        return f"{days} day{'s' if days != 1 else ''} left"

    @property
    def renewals_remaining(self):
        max_renewals = current_app.config['MAX_RENEWALS']
        return max(0, max_renewals - self.renewal_count)

    @cached_property
    def renew_blocked_reason(self):
        """Why this loan can't be self-renewed right now, or None if it can.
        Exposed separately from can_renew so the UI can explain the block
        instead of just disabling the button.

        Memoized: the last check hits the database, and every list of loans
        asks for this two or three times per row (can_renew, then the branch
        that decides whether to show the reason, then the reason itself).
        Cleared by _invalidate_derived() whenever this loan changes."""
        if self.status != 'active':
            return None  # not applicable; caller shouldn't be asking
        if self.due_state == 'overdue':
            return 'Overdue loans must be returned rather than renewed.'
        if self.renewals_remaining <= 0:
            return 'This loan has reached its renewal limit.'
        if self.book_id in Reservation.reserved_book_ids():
            return 'Another member is waiting for this title.'
        return None

    def _invalidate_derived(self):
        """Drop memoized derived values after a change to this loan, so a
        read following a write inside the same request isn't stale."""
        self.__dict__.pop('renew_blocked_reason', None)

    @property
    def can_renew(self):
        return self.status == 'active' and self.renew_blocked_reason is None

    def renew(self):
        """Extend the due date by one fresh loan period and record the
        renewal. Callers must check can_renew first -- this does not
        re-validate, so it can also be used by an admin override later."""
        loan_days = current_app.config['LOAN_PERIOD_DAYS']
        self.due_date = datetime.utcnow() + timedelta(days=loan_days)
        self.renewal_count += 1
        db.session.commit()
        self._invalidate_derived()

    def mark_returned(self):
        self.status = 'returned'
        self.return_date = datetime.utcnow()
        self.book.available_quantity += 1
        db.session.commit()
        self._invalidate_derived()


class Reservation(db.Model):
    __tablename__ = 'reservation'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False, index=True)
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active', index=True)  # active, fulfilled, expired, cancelled

    user = db.relationship('User', backref=db.backref(
        'reservations', lazy='dynamic', cascade='all, delete-orphan'))
    book = db.relationship('Book', backref=db.backref(
        'reservations', lazy='dynamic', cascade='all, delete-orphan'))

    @property
    def days_until_expiry(self):
        """Whole days until this reservation expires (calendar-date based,
        matching Borrowing.days_until_due -- including the same library-local
        timezone comparison)."""
        if self.expiration_date is None:
            return None
        return (to_local(self.expiration_date).date() - local_now().date()).days

    @property
    def expiry_label(self):
        days = self.days_until_expiry
        if days is None:
            return ''
        if days < 0:
            return 'Expired'
        if days == 0:
            return 'Expires today'
        return f"{days} day{'s' if days != 1 else ''} left"

    @cached_property
    def queue_position(self):
        """1-indexed position in this book's reservation queue (the oldest
        active reservation is #1), or None once this reservation is no
        longer active.

        Memoized alongside queue_length: the Reserved tab renders both for
        every reservation, and each one is its own query.

        Ties on reservation_date are broken by id, matching the ordering
        get_active_reservation uses to decide who is fulfilled next -- so
        "#1" here is always the same reservation that would actually be
        filled first.
        """
        if self.status != 'active':
            return None
        queue = Reservation._active_queues().get(self.book_id, [])
        if self.id in queue:
            return queue.index(self.id) + 1
        # Not in the batched snapshot -- e.g. added but not yet committed.
        # Fall back to asking the database directly rather than lying.
        ahead = Reservation.query.filter(
            Reservation.book_id == self.book_id,
            Reservation.status == 'active',
        ).filter(
            db.or_(
                Reservation.reservation_date < self.reservation_date,
                db.and_(
                    Reservation.reservation_date == self.reservation_date,
                    Reservation.id < self.id,
                ),
            )
        ).count()
        return ahead + 1

    @cached_property
    def queue_length(self):
        """Total number of members currently waiting for this book."""
        queues = Reservation._active_queues()
        if self.book_id in queues:
            return len(queues[self.book_id])
        return Reservation.query.filter_by(book_id=self.book_id, status='active').count()

    @property
    def queue_label(self):
        """Human-readable queue status, e.g. "You're next in line" or
        "#3 in line"."""
        position = self.queue_position
        if position is None:
            return ''
        if position == 1:
            return "You're next in line"
        return f'#{position} in line'

    @classmethod
    def _active_queues(cls):
        """{book_id: [reservation id, ...]} in queue order, for every active
        reservation, built in one query and reused for the whole request.

        Position and length were a query each, per reservation -- a member
        with thirty holds cost sixty round trips to render one screen. One
        ordered fetch answers both for every row. The ordering here must stay
        identical to get_active_reservation's (reservation_date, then id), or
        "#1 in line" would name someone other than whoever is actually filled
        next.
        """
        cached = has_app_context() and hasattr(g, '_active_queues')
        if cached:
            return g._active_queues
        queues = {}
        rows = db.session.query(cls.id, cls.book_id).filter_by(
            status='active').order_by(cls.reservation_date, cls.id).all()
        for reservation_id, book_id in rows:
            queues.setdefault(book_id, []).append(reservation_id)
        if has_app_context():
            g._active_queues = queues
        return queues

    @classmethod
    def reserved_book_ids(cls):
        """Every book id with at least one active reservation, fetched once
        per request and shared by all callers.

        Without this, "is anyone waiting for this title?" is one query per
        loan on a list screen. Answering it for the whole catalogue in a
        single query is cheaper than answering it five times individually,
        and keeps the query count flat as MAX_ACTIVE_LOANS grows.

        Cached on `g` because the answer must stay stable within one request
        but must never survive into the next one. Outside an application
        context (a script, a shell) it simply runs the query each time.
        """
        if not has_app_context():
            return {row[0] for row in
                    db.session.query(cls.book_id).filter_by(status='active').distinct()}
        if not hasattr(g, '_reserved_book_ids'):
            g._reserved_book_ids = {
                row[0] for row in
                db.session.query(cls.book_id).filter_by(status='active').distinct()
            }
        return g._reserved_book_ids

    @classmethod
    def get_active_reservation(cls, book_id):
        return cls.query.filter_by(book_id=book_id, status='active').order_by(
            cls.reservation_date, cls.id
        ).first()

    def fulfill(self):
        self.status = 'fulfilled'
        db.session.commit()

    def expire(self):
        self.status = 'expired'
        db.session.commit()


@event.listens_for(db.session, 'after_commit')
def _drop_request_scoped_caches(session):
    """Any commit can change who is waiting for a title, so the batched
    reservation lookups must not outlive it. Clearing here means the caches
    are correct by construction rather than by every caller remembering to
    invalidate them."""
    if has_app_context():
        g.pop('_reserved_book_ids', None)
        g.pop('_active_queues', None)
