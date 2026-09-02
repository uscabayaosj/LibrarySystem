import secrets
import time

from flask import current_app, g, has_app_context, url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import cached_property
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import make_transient_to_detached
from extensions import db
from localtime import to_local, local_now, local_today_start_utc

# Several display properties below issue their own query (a reservation
# lookup, a count). Templates read them more than once per object -- the
# dashboard alone asked for renew_blocked_reason three times per loan, via
# can_renew, then the elif, then the output -- which turned five loans into
# fifteen identical SELECTs. They are memoized with cached_property, which
# is safe because SQLAlchemy hands out a fresh instance per request and the
# session is torn down at the end of it, so a cached value never outlives
# the request that computed it. Mutating methods clear their own entries so
# a read-after-write inside one request still sees the truth.


class RowCache:
    """A process-level cache of one table's rows, as column values.

    Every request reads a couple of rows that almost never change -- the
    branding singleton and the signed-in user -- and on a serverless host
    each of those reads is a full round trip to the database before the page
    can start. Values, not instances, are what is cached: a hit rebuilds a
    fresh instance and attaches it to the request's session, so per-request
    memoization (cached_property) starts clean and callers can still edit
    and commit what they are handed. Any write to a cached row drops it from
    this process's cache via mapper events; other warm instances converge
    within the TTL, which is the staleness budget a caller accepts by
    reading through the cache at all."""

    def __init__(self, model, ttl_seconds=60):
        self.model = model
        self.ttl = ttl_seconds
        self._rows = {}

    def get(self, key):
        """A session-attached instance for `key`, or None on a miss."""
        entry = self._rows.get(key)
        if entry is None or time.monotonic() - entry[1] >= self.ttl:
            return None
        instance = self.model(**entry[0])
        make_transient_to_detached(instance)
        return db.session.merge(instance, load=False)

    def put(self, instance):
        values = {attr.key: getattr(instance, attr.key)
                  for attr in sa.inspect(self.model).column_attrs}
        self._rows[values['id']] = (values, time.monotonic())

    def forget(self, key=None):
        if key is None:
            self._rows.clear()
        else:
            self._rows.pop(key, None)

    def watch(self):
        """Drop a row from the cache whenever the mapper writes it."""
        def _forget(mapper, connection, target):
            self.forget(target.id)
        for name in ('after_insert', 'after_update', 'after_delete'):
            event.listen(self.model, name, _forget)
        return self


class OrganizationSettings(db.Model):
    """Singleton row (always id=1) holding the per-deployment branding: the
    organization's display name, an optional uploaded logo, and a custom
    theme color. A real table (rather than a config file) so an admin can
    change branding from the UI without redeploying or touching the
    environment."""
    __tablename__ = 'organization_settings'

    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(80), nullable=False, default='Library System')
    theme_color = db.Column(db.String(7))  # '#rrggbb', or None for the default palette
    # Where to reach a human: shown on error pages, which otherwise say
    # "contact the library desk" and name no desk. Per-deployment like the
    # rest of the branding, so it is editable in Admin -> Settings rather than
    # hardcoded. None falls back to the generic sentence.
    contact_note = db.Column(db.String(200))

    # The logo itself, stored as bytes rather than a filename on disk. See
    # branding_images.py's module docstring for why: a filename column only
    # works if the app process has a writable, *persistent* filesystem, and
    # this app has hit two hosts where that assumption fails (a Render disk
    # that turned out incompatible with its own plan, and Vercel's
    # serverless functions, which have no persistent disk on any plan). A
    # database column behaves the same everywhere Flask-SQLAlchemy already
    # runs, so there is nothing host-specific left to configure.
    logo_data = db.Column(db.LargeBinary)
    logo_content_type = db.Column(db.String(32))
    # Drives the cache-busting ?v= on every branding URL (see routes/branding.py)
    # -- the same role app.py's _stamp_static_url mtime stamp plays for
    # ordinary static files, which doesn't apply here since there's no file
    # to stat().
    logo_updated_at = db.Column(db.DateTime)

    # Every page reads this row (see RowCache for why it is cached). Readers
    # that must never lag -- the logo route, whose bytes the browser caches
    # immutably under a URL versioned by logo_updated_at, and the admin's
    # own settings form -- pass fresh=True and skip the cache.
    cache = None   # bound below the class, once it exists

    @classmethod
    def get(cls, fresh=False):
        """Fetch the singleton row, creating it with defaults on first use."""
        if not fresh:
            cached = cls.cache.get(1)
            if cached is not None:
                return cached
        settings = cls.query.get(1)
        if settings is None:
            settings = cls(id=1)
            db.session.add(settings)
            db.session.commit()
        cls.cache.put(settings)
        return settings

    @classmethod
    def forget(cls):
        cls.cache.forget()

    @property
    def logo_ready(self):
        """True once a logo has been uploaded. Unlike the old file-on-disk
        check this replaced, there is no drift to guard against: the bytes
        and the pointer are the same row, updated in the same transaction,
        so they cannot go out of sync with each other the way a database
        pointer and a separately-written file could."""
        return self.logo_data is not None

    @property
    def logo_cache_key(self):
        return int(self.logo_updated_at.timestamp()) if self.logo_updated_at else 0

    @property
    def logo_url(self):
        """Absolute URL for the <img> tag in the sidebar/hero mark, or None
        when there's no uploaded logo -- callers fall back to the bundled
        seal/brand mark in that case, the same way they always have."""
        if not self.logo_ready:
            return None
        return url_for('branding.logo', v=self.logo_cache_key)

    def icon_url(self, variant):
        """URL for one derived icon (see branding_images.ICON_SPECS for
        valid names), falling back to the bundled default icon of the same
        name when no logo is uploaded."""
        if not self.logo_ready:
            return url_for('static', filename='icons/%s.png' % variant)
        return url_for('branding.icon', variant=variant, v=self.logo_cache_key)

    @property
    def favicon_url(self):
        if not self.logo_ready:
            return url_for('static', filename='icons/favicon.ico')
        return url_for('branding.favicon', v=self.logo_cache_key)



OrganizationSettings.cache = RowCache(OrganizationSettings).watch()


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    # Null until the member finishes or skips the one-time welcome walkthrough
    # (see routes/member.py:welcome). Admins never see it, so this stays null
    # for every seeded/admin-created account without needing a special case.
    onboarding_completed_at = db.Column(db.DateTime, nullable=True)

    # A librarian-issued, single-use password reset. Only the hash is stored --
    # the plaintext code exists for exactly one response, the one that shows it
    # to the librarian, and is unrecoverable afterwards. See issue_reset_code().
    reset_code_hash = db.Column(db.String(255), nullable=True)
    reset_expires_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        # A password change consumes any outstanding reset, so a code issued at
        # the desk cannot be redeemed after the member has already got back in
        # some other way.
        self.clear_reset_code()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ---- Password reset (desk-issued) ---------------------------------------
    #
    # There is no mail server in this deployment and there deliberately isn't
    # one: PRODUCT.md principle 4 keeps the app free of external dependencies so
    # it runs on a restricted campus network. A self-service "email me a link"
    # flow would need SMTP the institution may not expose, and would fail
    # silently and unrecoverably when it did.
    #
    # What the library does have is a desk. So a reset is issued by a librarian
    # to a member standing in front of them: the app generates a one-time code,
    # shows it to the librarian once, and the member redeems it themselves --
    # the librarian never learns or sets the new password.

    # Digits and uppercase letters minus the pairs people misread when a code is
    # read aloud or copied off a screen: no O/0, I/1, S/5, Z/2.
    RESET_ALPHABET = 'ABCDEFGHJKLMNPQRTUVWXY346789'
    RESET_CODE_LENGTH = 10
    RESET_TTL_MINUTES = 30

    def issue_reset_code(self):
        """Generate a fresh single-use reset code, store only its hash, and
        return the plaintext once. Any previous code is invalidated."""
        code = ''.join(secrets.choice(self.RESET_ALPHABET)
                       for _ in range(self.RESET_CODE_LENGTH))
        self.reset_code_hash = generate_password_hash(code)
        self.reset_expires_at = (datetime.utcnow()
                                 + timedelta(minutes=self.RESET_TTL_MINUTES))
        return code

    def clear_reset_code(self):
        self.reset_code_hash = None
        self.reset_expires_at = None

    @property
    def reset_code_active(self):
        return bool(self.reset_code_hash
                    and self.reset_expires_at
                    and self.reset_expires_at > datetime.utcnow())

    def check_reset_code(self, code):
        """Constant-time-ish check of a submitted code. False for an expired,
        consumed, or never-issued code, so an attacker can't tell those apart."""
        if not self.reset_code_active or not code:
            return False
        return check_password_hash(self.reset_code_hash, code.strip().upper())

    # Read on every page: the tab bar badges loans and holds, the bell shows
    # unread notices, and <body> carries the overdue count for the PWA
    # home-screen badge. Four counts, one round trip -- on a serverless host
    # each query is a full trip to the database, and the four separate
    # COUNTs this replaced were most of the delay behind a tapped tab.
    @cached_property
    def _shell_counts(self):
        active = db.session.query(sa.func.count(Borrowing.id)).filter(
            Borrowing.user_id == self.id, Borrowing.status == 'active'
        ).scalar_subquery()
        # Cut off at local midnight, not utcnow() -- this count drives the
        # PWA home-screen badge, and against a raw UTC clock it went to 1
        # while the loan's own badge still read "Due today". See localtime.py.
        overdue = db.session.query(sa.func.count(Borrowing.id)).filter(
            Borrowing.user_id == self.id, Borrowing.status == 'active',
            Borrowing.due_date < local_today_start_utc()
        ).scalar_subquery()
        holds = db.session.query(sa.func.count(Reservation.id)).filter(
            Reservation.user_id == self.id, Reservation.status == 'active'
        ).scalar_subquery()
        unread = db.session.query(sa.func.count(Notification.id)).filter(
            Notification.user_id == self.id, Notification.read_at.is_(None)
        ).scalar_subquery()
        row = db.session.execute(sa.select(active, overdue, holds, unread)).one()
        return {'active': row[0], 'overdue': row[1],
                'holds': row[2], 'unread': row[3]}

    @property
    def active_borrowings(self):
        return self._shell_counts['active']

    @property
    def overdue_borrowings(self):
        return self._shell_counts['overdue']

    @property
    def active_reservations_count(self):
        return self._shell_counts['holds']

    @property
    def unread_notices(self):
        return self._shell_counts['unread']

    @cached_property
    def borrow_blocked_reason(self):
        """Why this member can't borrow anything right now, or None if they
        can. The sibling of Borrowing.renew_blocked_reason, and it exists for
        the same reason: the rules that stop a loan are knowable when the page
        is rendered, so the interface can say which one applies instead of
        offering a control the server will refuse.

        Before this existed, a blocked member saw a live Borrow button on
        every available title, agreed to a confirmation sheet promising a due
        date, and only then met a flash naming the rule -- repeatable once per
        title in the catalogue.

        Memoized because the catalogue asks once per card (twenty times a
        page) and the answer cannot change inside one request."""
        overdue_limit = current_app.config['MAX_OVERDUE_BEFORE_BLOCK']
        if self.overdue_borrowings >= overdue_limit:
            n = self.overdue_borrowings
            return (f"{n} overdue book{'s' if n != 1 else ''} "
                    f"{'are' if n != 1 else 'is'} blocking new loans — "
                    'return them to start borrowing again.')
        loan_limit = current_app.config['MAX_ACTIVE_LOANS']
        if self.active_borrowings >= loan_limit:
            return (f"You're at your {loan_limit}-book limit — "
                    'return one to borrow again.')
        return None

    def _invalidate_borrow_state(self):
        """Drop the memoized loan/overdue counts after a borrow or return, so
        a read following a write inside one request isn't stale."""
        for key in ('_shell_counts', 'borrow_blocked_reason'):
            self.__dict__.pop(key, None)



# Flask-Login reloads this row on every request; see app.load_user. A shorter
# TTL than the branding row: this is the window in which a deleted account or
# an old password can still load on a warm instance that did not see the write.
User.cache = RowCache(User, ttl_seconds=30).watch()

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
        # Derived from due_state rather than recomputed, so this can never
        # disagree with the badge, the colour, or the renewal block -- all of
        # which already come from that one property.
        return self.due_state == 'overdue'

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
            limit = current_app.config['MAX_RENEWALS']
            times = 'once' if limit == 1 else f'{limit} times'
            return f"You've already renewed this {times} — that's the limit."
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
        # Clamped rather than a bare +1: if a book's quantity was edited down
        # while copies were out, letting available_quantity climb past it
        # would violate the one canonical circulation-truth invariant this
        # whole system builds on (see PRODUCT.md's Product Principles #1).
        self.book.available_quantity = min(
            self.book.quantity, self.book.available_quantity + 1
        )
        db.session.commit()
        self._invalidate_derived()

    # A mis-clicked check-in used to be permanent: the row's control became an
    # em-dash and there was no inverse anywhere in the app. On a desk doing
    # thirty returns in a morning that is a real and unrecoverable mistake, so
    # the receipt now carries an undo for a few minutes.
    UNDO_WINDOW_MINUTES = 15

    @property
    def undo_return_blocked_reason(self):
        """Why this return can't be undone, or None if it can.

        Refuses rather than guesses. Putting a copy back on loan is only safe
        while nothing else has happened to it -- if the shelf copy has since
        gone out to someone else, silently decrementing availability again
        would hand out a copy the library does not physically have.
        """
        if self.status != 'returned' or self.return_date is None:
            return 'This loan is not checked in.'
        age = datetime.utcnow() - self.return_date
        if age > timedelta(minutes=self.UNDO_WINDOW_MINUTES):
            return (f'Check-ins can only be undone within '
                    f'{self.UNDO_WINDOW_MINUTES} minutes.')
        if self.book.available_quantity < 1:
            return ('Every copy is out again — undoing this would lend a copy '
                    'the shelf does not have.')
        return None

    def undo_return(self):
        """Put this loan back on loan. Caller must check
        undo_return_blocked_reason first."""
        self.status = 'active'
        self.return_date = None
        self.book.available_quantity = max(0, self.book.available_quantity - 1)
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


class Notification(db.Model):
    """An in-app notice for one member.

    In-app rather than push or email, for the same reason the password reset is
    desk-issued: web push needs VAPID keys and a third-party push service, and
    email needs SMTP. Both are external dependencies this deployment
    deliberately does without (PRODUCT.md principle 4), and a notification
    channel that silently fails on a restricted network is worse than none --
    it would let the library believe members had been told.

    So these are records the member reads when they open the app, which is the
    thing the borrower persona already does daily to check due dates.
    """
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    kind = db.Column(db.String(32), nullable=False)  # hold_ready | due_soon | overdue | checked_out
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.String(400))
    # A route name plus optional id, resolved in the template. Storing a built
    # URL would bake the deployment's script-root into the database.
    link_endpoint = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime, nullable=True)

    # What makes generation idempotent. The librarian runs the circulation
    # sweep whenever they like -- several times a day in a busy week -- and a
    # member must not collect five copies of "due in 2 days" because of it.
    # Unique per user, so one loan crossing into due-soon and later into
    # overdue still produces two distinct notices.
    dedupe_key = db.Column(db.String(80), nullable=False)

    user = db.relationship('User', backref=db.backref(
        'notifications', lazy='dynamic', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'dedupe_key', name='uq_notification_user_dedupe'),
    )

    @classmethod
    def push(cls, user_id, kind, title, body=None, link_endpoint=None, dedupe_key=None):
        """Create a notice unless this user already has one with the same
        dedupe key. Returns the Notification, or None if it was a duplicate.

        Does not commit -- callers batch these inside their own transaction so
        a failed sweep doesn't leave half the notices behind.
        """
        key = dedupe_key or f'{kind}:{title}'
        exists = cls.query.filter_by(user_id=user_id, dedupe_key=key).first()
        if exists:
            return None
        note = cls(user_id=user_id, kind=kind, title=title, body=body,
                   link_endpoint=link_endpoint, dedupe_key=key)
        db.session.add(note)
        return note

    @classmethod
    def unread_count(cls, user_id):
        return cls.query.filter_by(user_id=user_id, read_at=None).count()

    @classmethod
    def sweep_loans(cls):
        """Raise due-soon and overdue notices for every active loan.

        Called from the librarian's circulation run rather than a cron job:
        this deployment has no scheduler, and inventing one would add the
        first background process to an app that is currently a single web
        service. The desk runs this daily; the dedupe key makes running it
        five times a day harmless.

        Returns how many new notices were created.
        """
        created = 0
        loans = Borrowing.query.options(
            db.joinedload(Borrowing.book)
        ).filter_by(status='active').all()
        for loan in loans:
            state = loan.due_state
            if state == 'overdue':
                days = loan.days_overdue
                note = cls.push(
                    loan.user_id, 'overdue',
                    f'"{loan.book.title}" is overdue',
                    f'It was due {to_local(loan.due_date).strftime("%b %d, %Y")}'
                    f' — {days} day{"s" if days != 1 else ""} ago. '
                    'Please return it to the desk.',
                    'member.borrowing_history',
                    f'overdue:{loan.id}',
                )
            elif state in ('today', 'soon'):
                # Built from the day count rather than reusing due_label. That
                # label is written to stand alone in a badge ("2 days left"),
                # and dropping it into this sentence frame produced
                # '"Pedagogy of the Oppressed" is 2 days left'.
                days = loan.days_until_due
                if days == 0:
                    when = 'is due today'
                elif days == 1:
                    when = 'is due tomorrow'
                else:
                    when = f'is due in {days} days'
                note = cls.push(
                    loan.user_id, 'due_soon',
                    f'"{loan.book.title}" {when}',
                    'Renew it from My Loans if nobody else is waiting for it.',
                    'member.borrowing_history',
                    f'due_soon:{loan.id}',
                )
            else:
                continue
            if note is not None:
                created += 1
        return created


@event.listens_for(db.session, 'after_commit')
def _drop_request_scoped_caches(session):
    """Any commit can change who is waiting for a title, so the batched
    reservation lookups must not outlive it. Clearing here means the caches
    are correct by construction rather than by every caller remembering to
    invalidate them."""
    if has_app_context():
        g.pop('_reserved_book_ids', None)
        g.pop('_active_queues', None)


def desk_counts():
    """The seven numbers on the librarian's dashboard, in one round trip.

    Seven COUNTs over four tables; each used to be its own query, and on a
    serverless host each query is a full trip to the database. Scalar
    subqueries let one SELECT return them all. Deliberately *not* cached
    across requests: the desk checks a book in and expects the tile to move,
    and a cross-instance TTL would show them a number they know is wrong."""
    def count(model, *criteria):
        return db.session.query(sa.func.count(model.id)).filter(*criteria).scalar_subquery()

    today = local_today_start_utc()
    available_ids = db.session.query(Book.id).filter(Book.available_quantity > 0)
    row = db.session.execute(sa.select(
        count(Book),
        count(User, User.is_admin == False),  # noqa: E712 -- SQL comparison
        count(Borrowing, Borrowing.status == 'active'),
        # Local midnight, not utcnow(): the Overdue tile links straight to
        # the list below it, and against a raw UTC clock the tile said 5
        # while the list badged 4 -- the fifth was due *today*.
        count(Borrowing, Borrowing.status == 'active', Borrowing.due_date < today),
        count(Reservation, Reservation.status == 'active'),
        count(Book, Book.available_quantity > 0),
        # Holds waiting on a copy that is already back on the shelf.
        count(Reservation, Reservation.status == 'active',
              Reservation.book_id.in_(available_ids)),
    )).one()
    keys = ('total_books', 'total_members', 'active_borrowings', 'overdue_count',
            'active_reservations', 'available_books', 'ready_to_fulfil')
    return dict(zip(keys, row))
