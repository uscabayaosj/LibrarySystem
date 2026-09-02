from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from models import db, Book, User, Borrowing, Reservation, OrganizationSettings, Notification
from datetime import datetime, timedelta
from theming import normalize_hex, build_theme_css
from branding_images import validate_and_reencode, LogoValidationError
from validation import length_errors, max_length, FIELD_LABELS
from localtime import local_today_start_utc, to_local

bp = Blueprint('admin', __name__, url_prefix='/admin')

# How many of a member's reservations the detail page shows before it just
# reports the total. Their loan history is paginated; this list is short in
# practice, so a cap plus an honest count beats a second page control.
RESERVATION_PREVIEW_LIMIT = 25


@bp.before_request
@login_required
def restrict_to_admins():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('member.dashboard'))


# ---- Sortable columns --------------------------------------------------------
#
# Server-side, not a client-side table script. All three admin lists paginate,
# so sorting the rendered rows would reorder 30 records out of 300 and present
# the result as "sorted by worst overdue" -- the same class of lie the bulk
# select-all label used to tell. The sort travels in the querystring, so it
# survives pagination, search, a filter change and a bookmark.
#
# Each table declares a closed map of key -> column. A request naming anything
# else falls back to the default rather than erroring, because a sort key is
# not worth a 400 to a librarian who edited a URL.

def _sorted_query(query, sort, direction, columns, default_key, tiebreak):
    """Apply ?sort=&dir= to a query. Returns (query, key, direction)."""
    key = sort if sort in columns else default_key
    direction = 'desc' if direction == 'desc' else 'asc'
    col = columns[key]
    primary = col.desc() if direction == 'desc' else col.asc()
    # The tiebreak is not decoration. Without a deterministic second key, two
    # loans due the same day can swap places between the query for page 1 and
    # the query for page 2, which silently shows one record twice and skips
    # another -- the failure mode a librarian would experience as "a book
    # vanished from the list".
    return query.order_by(primary, tiebreak.asc()), key, direction


_LEDGER_SORTS = {
    'book': Book.title,
    'member': User.username,
    'borrowed': Borrowing.borrow_date,
    'due': Borrowing.due_date,
}
_BOOK_SORTS = {
    'title': Book.title,
    'author': Book.author,
    'category': Book.category,
    'available': Book.available_quantity,
}
_MEMBER_SORTS = {
    'member': User.username,
    'email': User.email,
    'joined': User.member_since,
}


def _books_context(page=1, search='', form_values=None, form_errors=None,
                   field_errors=None, sort=None, direction=None):
    per_page = 20
    query = Book.query
    if search:
        query = query.filter(
            db.or_(
                Book.title.ilike(f'%{search}%'),
                Book.author.ilike(f'%{search}%'),
                Book.isbn.ilike(f'%{search}%'),
                Book.category.ilike(f'%{search}%'),
            )
        )
    query, sort_key, sort_dir = _sorted_query(
        query, sort, direction, _BOOK_SORTS, 'title', Book.id)
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    # How many copies of each visible title are out, in one grouped query
    # rather than a COUNT per row. The delete control needs this at render
    # time: a title with copies on loan can't be deleted, and the row should
    # say so instead of raising a danger sheet the server then refuses.
    book_ids = [b.id for b in pagination.items]
    on_loan_counts = {}
    if book_ids:
        on_loan_counts = dict(db.session.query(
            Borrowing.book_id, db.func.count(Borrowing.id)
        ).filter(
            Borrowing.book_id.in_(book_ids), Borrowing.status == 'active'
        ).group_by(Borrowing.book_id).all())
    return {
        'pagination': pagination,
        'search': search,
        'form_values': form_values or {},
        'form_errors': form_errors,
        'field_errors': field_errors or {},
        'on_loan_counts': on_loan_counts,
        'sort_key': sort_key,
        'sort_dir': sort_dir,
    }


@bp.route('/dashboard')
def dashboard():
    now = datetime.utcnow()
    total_books = Book.query.count()
    total_members = User.query.filter_by(is_admin=False).count()
    active_borrowings = Borrowing.query.filter_by(status='active').count()
    # Local midnight, not utcnow(): this tile links straight to the list
    # below it, and against a raw UTC clock the tile said 5 while the list it
    # opened badged 4 -- the fifth was due *today*. See localtime.py.
    overdue_count = Borrowing.query.filter(
        Borrowing.status == 'active',
        Borrowing.due_date < local_today_start_utc()
    ).count()
    active_reservations = Reservation.query.filter_by(status='active').count()
    available_books = Book.query.filter(Book.available_quantity > 0).count()

    # The lane the librarian's day actually runs on. Worst first, because that
    # is the order a chase list is worked -- the same order the Overdue filter
    # uses, so opening "see all" doesn't reshuffle what they were reading.
    overdue_loans = Borrowing.query.options(
        db.joinedload(Borrowing.user),
        db.joinedload(Borrowing.book)
    ).filter(
        Borrowing.status == 'active',
        Borrowing.due_date < local_today_start_utc(),
    ).order_by(Borrowing.due_date.asc()).limit(6).all()

    # Due today and in the next few days: what will be late if nobody acts.
    # Bounded by the same due-soon window the member's badge uses, so the two
    # roles agree about which loans are "nearly due".
    soon_cutoff = local_today_start_utc() + timedelta(days=4)
    due_soon_loans = Borrowing.query.options(
        db.joinedload(Borrowing.user),
        db.joinedload(Borrowing.book)
    ).filter(
        Borrowing.status == 'active',
        Borrowing.due_date >= local_today_start_utc(),
        Borrowing.due_date < soon_cutoff,
    ).order_by(Borrowing.due_date.asc()).limit(6).all()

    # Holds waiting on a copy that is already back on the shelf -- the work
    # "Process Reservations" exists to do, surfaced so the librarian knows
    # there is something to process before pressing it.
    ready_to_fulfil = Reservation.query.filter(
        Reservation.status == 'active',
        Reservation.book_id.in_(
            db.session.query(Book.id).filter(Book.available_quantity > 0)
        ),
    ).count()

    recent_borrowings = Borrowing.query.options(
        db.joinedload(Borrowing.user),
        db.joinedload(Borrowing.book)
    ).order_by(Borrowing.borrow_date.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_books=total_books,
        total_members=total_members,
        active_borrowings=active_borrowings,
        overdue_count=overdue_count,
        active_reservations=active_reservations,
        available_books=available_books,
        recent_borrowings=recent_borrowings,
        overdue_loans=overdue_loans,
        due_soon_loans=due_soon_loans,
        ready_to_fulfil=ready_to_fulfil,
        now=now,
    )


@bp.route('/books')
def books():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    return render_template('admin/books.html', **_books_context(
        page, search,
        sort=request.args.get('sort'), direction=request.args.get('dir')))


@bp.route('/books/add', methods=['GET'])
def add_book_form():
    """Refreshing after a failed Add Book used to hit a POST-only URL and get
    a raw, unstyled Werkzeug 405 with no way back into the app. The form has
    no page of its own -- it is a disclosure panel on the catalogue -- so a
    GET here just reopens it there."""
    return redirect(url_for('admin.books') + '#add-book')


@bp.route('/books/add', methods=['POST'])
def add_book():
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    isbn = request.form.get('isbn', '').strip()
    category = request.form.get('category', '').strip()
    publisher = request.form.get('publisher', '').strip()
    pub_year = request.form.get('publication_year', type=int)
    description = request.form.get('description', '').strip()
    quantity = request.form.get('quantity', 1, type=int)

    field_errors = {}
    if not title:
        field_errors['title'] = 'Title is required.'
    if not author:
        field_errors['author'] = 'Author is required.'
    if not isbn:
        field_errors['isbn'] = 'ISBN is required.'
    length_values = {
        'title': title, 'author': author, 'isbn': isbn,
        'category': category, 'publisher': publisher,
    }
    for field in length_values:
        limit = max_length(Book, field)
        value = length_values[field]
        if limit is not None and isinstance(value, str) and len(value) > limit and field not in field_errors:
            field_errors[field] = f'{FIELD_LABELS.get(field, field.capitalize())} must be {limit} characters or fewer (you entered {len(value)}).'
    if quantity is None or quantity < 1:
        field_errors['quantity'] = 'Quantity must be at least 1.'
        quantity = 1
    existing = Book.query.filter_by(isbn=isbn).first() if isbn else None
    if existing:
        field_errors['isbn'] = f'A book with ISBN {isbn} already exists ({existing.title}).'

    errors = list(field_errors.values())
    if errors:
        # One summary flash, not one per field. Every message is already
        # rendered inline against its own input, so flashing each of them too
        # turned four problems into eight on-screen messages saying the same
        # things twice.
        count = len(errors)
        flash(f"The book wasn't added — {count} field{'s need' if count != 1 else ' needs'} "
              'fixing below.', 'warning')
        return render_template(
            'admin/books.html',
            **_books_context(1, '', form_values=request.form, form_errors=errors, field_errors=field_errors)
        )

    book = Book(
        title=title, author=author, isbn=isbn, category=category,
        publisher=publisher, publication_year=pub_year,
        description=description, quantity=quantity,
        available_quantity=quantity
    )
    db.session.add(book)
    db.session.commit()
    flash(f'Book "{title}" added successfully.', 'success')
    return redirect(url_for('admin.books'))


@bp.route('/books/<int:id>/edit', methods=['GET', 'POST'])
def edit_book(id):
    book = Book.query.get_or_404(id)
    active_loans = Borrowing.query.filter_by(book_id=id, status='active').count()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        category = request.form.get('category', '').strip()
        publisher = request.form.get('publisher', '').strip()
        new_quantity = request.form.get('quantity', book.quantity, type=int)

        field_errors = {}
        if not title:
            field_errors['title'] = 'Title is required.'
        if not author:
            field_errors['author'] = 'Author is required.'
        if not isbn:
            field_errors['isbn'] = 'ISBN is required.'
        length_values = {'title': title, 'author': author, 'isbn': isbn, 'category': category, 'publisher': publisher}
        for field in length_values:
            limit = max_length(Book, field)
            value = length_values[field]
            if limit is not None and isinstance(value, str) and len(value) > limit and field not in field_errors:
                field_errors[field] = f'{FIELD_LABELS.get(field, field.capitalize())} must be {limit} characters or fewer (you entered {len(value)}).'
        if new_quantity is None or new_quantity < 0:
            field_errors['quantity'] = 'Quantity cannot be negative.'
            new_quantity = book.quantity
        elif new_quantity < active_loans:
            # Circulation-truth guardrail (PRODUCT.md Principle #1): dropping
            # quantity below what's currently checked out would produce a
            # nonsensical negative available count downstream.
            field_errors['quantity'] = (
                f'{active_loans} currently on loan — quantity can\'t go below {active_loans}.'
            )
            new_quantity = book.quantity
        duplicate = Book.query.filter(Book.isbn == isbn, Book.id != id).first() if isbn else None
        if duplicate:
            field_errors['isbn'] = f'Another book already uses ISBN {isbn} ({duplicate.title}).'

        if field_errors:
            for msg in field_errors.values():
                flash(msg, 'warning')
            return render_template(
                'admin/edit_book.html', book=book, form_values=request.form,
                field_errors=field_errors, active_loans=active_loans,
            )

        book.title = title
        book.author = author
        book.isbn = isbn
        book.category = category
        book.publisher = publisher
        book.publication_year = request.form.get('publication_year', type=int)
        book.description = request.form.get('description', '').strip()

        diff = new_quantity - book.quantity
        book.quantity = new_quantity
        book.available_quantity = max(0, book.available_quantity + diff)
        db.session.commit()
        flash('Book updated successfully.', 'success')
        return redirect(url_for('admin.books'))
    return render_template('admin/edit_book.html', book=book, form_values=None, field_errors={}, active_loans=active_loans)


@bp.route('/books/<int:id>/delete', methods=['POST'])
def delete_book(id):
    book = Book.query.get_or_404(id)
    active_borrowings = Borrowing.query.filter_by(book_id=id, status='active').count()
    if active_borrowings > 0:
        copies = f"{active_borrowings} copy" if active_borrowings == 1 else f"{active_borrowings} copies"
        flash(f'"{book.title}" still has {copies} on loan. Check them in first, '
              'then delete the title.', 'warning')
        return redirect(url_for('admin.books'))
    title = book.title
    db.session.delete(book)  # cascade removes historical borrowings/reservations
    db.session.commit()
    flash(f'Book "{title}" deleted.', 'success')
    return redirect(url_for('admin.books'))


@bp.route('/members')
def members():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '').strip()

    query = User.query.filter_by(is_admin=False)
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
            )
        )
    query, sort_key, sort_dir = _sorted_query(
        query, request.args.get('sort'), request.args.get('dir'),
        _MEMBER_SORTS, 'member', User.id)
    members_pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Aggregate loan counts for the visible members in two queries instead of
    # running a COUNT per row (avoids the N+1 on this page).
    now = datetime.utcnow()
    member_ids = [m.id for m in members_pagination.items]
    active_counts, overdue_counts = {}, {}
    if member_ids:
        rows = db.session.query(
            Borrowing.user_id, db.func.count(Borrowing.id)
        ).filter(
            Borrowing.user_id.in_(member_ids), Borrowing.status == 'active'
        ).group_by(Borrowing.user_id).all()
        active_counts = dict(rows)
        rows = db.session.query(
            Borrowing.user_id, db.func.count(Borrowing.id)
        ).filter(
            Borrowing.user_id.in_(member_ids),
            Borrowing.status == 'active',
            Borrowing.due_date < local_today_start_utc(),
        ).group_by(Borrowing.user_id).all()
        overdue_counts = dict(rows)

    return render_template(
        'admin/members.html',
        pagination=members_pagination,
        search=search,
        now=now,
        active_counts=active_counts,
        overdue_counts=overdue_counts,
        sort_key=sort_key,
        sort_dir=sort_dir,
    )


@bp.route('/members/<int:id>')
def member_detail(id):
    member = User.query.get_or_404(id)
    if member.is_admin:
        flash('Invalid member.', 'danger')
        return redirect(url_for('admin.members'))
    # Both lists grow for the life of the account, so neither is fetched
    # whole: loan history is paginated, and the shorter reservation list is
    # capped with the total shown alongside it so nothing looks silently
    # truncated.
    page = request.args.get('page', 1, type=int)
    borrowings_pagination = Borrowing.query.options(
        db.joinedload(Borrowing.book)
    ).filter_by(user_id=id).order_by(
        Borrowing.borrow_date.desc()
    ).paginate(page=page, per_page=25, error_out=False)

    reservation_query = Reservation.query.options(
        db.joinedload(Reservation.book)
    ).filter_by(user_id=id).order_by(Reservation.reservation_date.desc())
    reservation_total = reservation_query.count()
    reservations = reservation_query.limit(RESERVATION_PREVIEW_LIMIT).all()

    now = datetime.utcnow()
    return render_template(
        'admin/member_detail.html',
        member=member,
        borrowings=borrowings_pagination.items,
        pagination=borrowings_pagination,
        reservations=reservations,
        reservation_total=reservation_total,
        reservation_limit=RESERVATION_PREVIEW_LIMIT,
        now=now,
    )


@bp.route('/members/<int:id>/reset-password', methods=['POST'])
def issue_password_reset(id):
    """Issue a one-time reset code for a member standing at the desk.

    The librarian identifies the person; the app can't. The code is shown to
    the librarian exactly once, in the flash below, and only its hash is
    stored -- so this route can hand out access but can never be used to
    recover an existing password, and the librarian never learns the new one
    the member chooses.
    """
    member = User.query.get_or_404(id)
    if member.is_admin:
        # Admin credentials are provisioned out of band (ADMIN_PASSWORD at
        # first boot); letting one admin reset another from the UI would make
        # the seeded account recoverable by anyone who reaches this page.
        flash('Administrator passwords are set through the deployment, not here.', 'warning')
        return redirect(url_for('admin.member_detail', id=id))

    code = member.issue_reset_code()
    db.session.commit()
    flash(f'One-time code for {member.username}: {code} — write it down now, '
          f'it is not shown again and expires in {User.RESET_TTL_MINUTES} minutes. '
          'They enter it at Sign in → Forgot password to choose their own new password.',
          'warning')
    return redirect(url_for('admin.member_detail', id=id))


@bp.route('/members/<int:id>/delete', methods=['POST'])
def delete_member(id):
    member = User.query.get_or_404(id)
    if member.is_admin:
        flash('Cannot delete admin users.', 'danger')
        return redirect(url_for('admin.members'))
    active_count = Borrowing.query.filter_by(user_id=id, status='active').count()
    if active_count > 0:
        loans = 'one book' if active_count == 1 else f'{active_count} books'
        flash(f'{member.username} still has {loans} out. Check them in first, '
              'then delete the account.', 'warning')
        return redirect(url_for('admin.members'))
    username = member.username
    db.session.delete(member)  # cascade removes history and reservations
    db.session.commit()
    flash(f'Member "{username}" deleted.', 'success')
    return redirect(url_for('admin.members'))


@bp.route('/borrowing-history')
def borrowing_history():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    filter_status = request.args.get('status', '').strip()
    search_term = request.args.get('search', '').strip()

    now = datetime.utcnow()
    # Joined up front, before anything filters or sorts on them: both the
    # search and the book/member sort keys reference these tables, and adding
    # the join afterwards leaves SQLAlchemy to invent a cross join.
    query = Borrowing.query.options(
        db.joinedload(Borrowing.user),
        db.joinedload(Borrowing.book)
    ).join(Borrowing.book).join(Borrowing.user)
    if filter_status == 'overdue':
        # Overdue isn't a stored status -- it's active plus a past due date.
        query = query.filter(Borrowing.status == 'active',
                             Borrowing.due_date < local_today_start_utc())
    elif filter_status in ('active', 'returned'):
        query = query.filter(Borrowing.status == filter_status)
    else:
        filter_status = ''

    # "Who has this book?" was a paging exercise at 30 records a page -- this
    # is the one list of the three that had no search, and it is the one a
    # patron standing at the desk asks about.
    if search_term:
        like = f'%{search_term}%'
        query = query.filter(
            db.or_(Book.title.ilike(like), Book.isbn.ilike(like),
                   User.username.ilike(like))
        )

    # The default still depends on the lane: under Overdue, worst-first, because
    # that is the order a chase list is worked. Ordering every filter by
    # borrow_date put the 26-days-late item *below* the 7-days-late one.
    sort = request.args.get('sort')
    direction = request.args.get('dir')
    if sort in _LEDGER_SORTS:
        query, sort_key, sort_dir = _sorted_query(
            query, sort, direction, _LEDGER_SORTS, 'due', Borrowing.id)
    elif filter_status == 'overdue':
        query, sort_key, sort_dir = _sorted_query(
            query, 'due', 'asc', _LEDGER_SORTS, 'due', Borrowing.id)
    else:
        query, sort_key, sort_dir = _sorted_query(
            query, 'borrowed', 'desc', _LEDGER_SORTS, 'borrowed', Borrowing.id)
    history_pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template(
        'admin/borrowing_history.html',
        pagination=history_pagination,
        filter_status=filter_status,
        search_term=search_term,
        sort_key=sort_key,
        sort_dir=sort_dir,
        now=now,
    )


def _back_to_ledger():
    """Return to the ledger view the librarian acted from.

    The bulk path already carried `status` through; the single check-in did
    not, so returning one book from the Overdue filter dropped the filter and
    landed on the unfiltered ledger -- twenty times over in a returns run.
    """
    return redirect(url_for(
        'admin.borrowing_history',
        status=request.form.get('status', '') or None,
        search=request.form.get('search', '') or None,
        page=request.form.get('page', type=int) or None,
    ))


@bp.route('/return-book/<int:id>', methods=['POST'])
def return_book(id):
    borrowing = Borrowing.query.get_or_404(id)
    if borrowing.status != 'active':
        flash('This book has already been returned.', 'info')
        return _back_to_ledger()
    borrowing.mark_returned()
    # The receipt carries its own inverse. A check-in is the single most
    # repeated destructive-ish action at the desk and it had no undo at all;
    # a confirmation dialog on every one of thirty returns is the wrong
    # answer (it taxes the 29 correct ones to catch the 1 mistake), so the
    # cheap control goes on the outcome instead.
    flash(f'"{borrowing.book.title}" returned by {borrowing.user.username}.',
          f'success|undo:{borrowing.id}')
    return _back_to_ledger()


@bp.route('/return-book/<int:id>/undo', methods=['POST'])
def undo_return(id):
    borrowing = Borrowing.query.get_or_404(id)
    blocked = borrowing.undo_return_blocked_reason
    if blocked:
        flash(blocked, 'warning')
        return _back_to_ledger()
    borrowing.undo_return()
    flash(f'"{borrowing.book.title}" is back on loan to '
          f'{borrowing.user.username}.', 'info')
    return _back_to_ledger()


@bp.route('/return-books/bulk', methods=['POST'])
def bulk_return_books():
    ids = request.form.getlist('borrowing_ids', type=int)
    if not ids:
        flash('No loans were selected.', 'warning')
        return _back_to_ledger()

    borrowings = Borrowing.query.filter(
        Borrowing.id.in_(ids), Borrowing.status == 'active'
    ).all()
    count = len(borrowings)
    titles = [b.book.title for b in borrowings]
    for borrowing in borrowings:
        borrowing.mark_returned()  # commits per-row, same as the single check-in path

    if count:
        # Name the records, the way the single check-in path does. A bare count
        # is the one receipt a mis-ticked checkbox stays invisible behind, and
        # this flash is the only record the action leaves.
        if count <= 3:
            named = ', '.join(f'"{t}"' for t in titles)
            flash(f'Checked in {named}.', 'success')
        else:
            named = ', '.join(f'"{t}"' for t in titles[:3])
            flash(f'Checked in {count} books: {named}, '
                  f'and {count - 3} more.', 'success')
    else:
        flash('Those loans were already returned.', 'info')
    return _back_to_ledger()


@bp.route('/check-reservations', methods=['POST'])
def check_reservations():
    now = datetime.utcnow()
    loan_days = current_app.config['LOAN_PERIOD_DAYS']

    # Expire overdue reservations.
    expired = Reservation.query.filter(
        Reservation.expiration_date < now,
        Reservation.status == 'active'
    ).all()
    for r in expired:
        r.status = 'expired'

    # Fulfil the reservation queue for every title that has copies free,
    # draining as many reservations as there is availability.
    fulfilled_count = 0
    fulfilled_notes = []
    available_books = Book.query.filter(Book.available_quantity > 0).all()
    for book in available_books:
        while book.available_quantity > 0:
            active_reservation = Reservation.get_active_reservation(book.id)
            if not active_reservation:
                break
            active_reservation.status = 'fulfilled'
            book.available_quantity -= 1
            # The member is told. Before notifications existed this moment --
            # the one the entire queue feature builds toward -- reached them
            # only if they happened to open the app and notice a card had
            # changed, and the card had in fact vanished (see the fulfilled
            # filter fix in routes/member.py:reservations).
            Notification.push(
                active_reservation.user_id, 'hold_ready',
                f'"{book.title}" is ready to collect',
                f'Your hold came up. Collect it from the desk within '
                f'{current_app.config["RESERVATION_HOLD_DAYS"]} days.',
                'member.reservations',
                f'hold_ready:{active_reservation.id}',
            )
            db.session.add(Borrowing(
                user_id=active_reservation.user_id,
                book_id=book.id,
                due_date=now + timedelta(days=loan_days)
            ))
            fulfilled_notes.append((active_reservation.user.username, book.title))
            fulfilled_count += 1

    # Same sweep, same trip: raise due-soon and overdue notices for every
    # active loan. This app has no scheduler, and this is the button a
    # librarian already presses daily, so it is where recurring work belongs
    # until there is somewhere better. Idempotent -- see Notification.sweep_loans.
    loan_notices = Notification.sweep_loans()

    db.session.commit()

    # This button issues real loans on members' behalf, and the librarian then
    # has to physically pull those books off a shelf. "0 expired, 1 fulfilled"
    # read like cron output and named neither the member nor the title, so the
    # one action with a physical consequence left no usable record. Say who
    # gets what; keep it as a warning-tier flash so it doesn't self-dismiss
    # after six seconds like a routine success.
    if fulfilled_notes:
        lines = '; '.join(f'"{title}" for {who}' for who, title in fulfilled_notes[:6])
        more = '' if len(fulfilled_notes) <= 6 else f'; and {len(fulfilled_notes) - 6} more'
        flash(f'Set aside {fulfilled_count} book{"s" if fulfilled_count != 1 else ""} '
              f'for collection — {lines}{more}. '
              f'{len(expired)} lapsed hold{"s" if len(expired) != 1 else ""} cleared, '
              f'{loan_notices} due/overdue notice{"s" if loan_notices != 1 else ""} sent.',
              'warning')
    elif expired:
        flash(f'{len(expired)} lapsed hold{"s" if len(expired) != 1 else ""} cleared, '
              f'{loan_notices} due/overdue notice{"s" if loan_notices != 1 else ""} sent. '
              'No queues could be filled — no reserved title has a copy free.', 'info')
    elif loan_notices:
        flash(f'{loan_notices} due/overdue notice{"s" if loan_notices != 1 else ""} sent. '
              'No holds have lapsed and no reserved title has a copy free.', 'info')
    else:
        flash('Nothing to do — no holds have lapsed, no reserved title has a '
              'copy free, and every member is already up to date.', 'info')
    return redirect(url_for('admin.dashboard'))


@bp.route('/settings/theme-preview')
def theme_preview():
    """The generated accent tokens for a candidate colour, as JSON.

    Saving branding repaints every screen for every member of the institution,
    and it did that from an un-previewed colour picker with no way to see the
    result first. The generator lives on the server (theming.build_theme),
    so the honest preview asks the server what it *would* produce rather than
    reimplementing the ramp in JavaScript and drifting from it.
    """
    css = build_theme_css(normalize_hex(request.args.get('color', '')) or '')
    return jsonify({'css': css})


@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    org_settings = OrganizationSettings.get(fresh=True)

    if request.method == 'POST':
        org_name = request.form.get('org_name', '').strip()
        contact_note = request.form.get('contact_note', '').strip()
        theme_color_input = request.form.get('theme_color', '').strip()
        remove_logo = request.form.get('remove_logo') == 'on'
        logo_file = request.files.get('logo')

        errors = []
        if not org_name:
            errors.append('Organization name is required.')
        elif len(org_name) > 80:
            errors.append('Organization name must be 80 characters or fewer.')
        if len(contact_note) > 200:
            errors.append('Contact line must be 200 characters or fewer.')

        normalized_color = None
        if theme_color_input:
            normalized_color = normalize_hex(theme_color_input)
            if not normalized_color:
                errors.append('Theme color must be a valid hex color, e.g. #292168.')

        new_logo_data = new_logo_content_type = None
        if logo_file and logo_file.filename:
            try:
                new_logo_data, new_logo_content_type = validate_and_reencode(logo_file)
            except LogoValidationError as e:
                errors.append(str(e))

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template(
                'admin/settings.html',
                org_settings=org_settings,
                form_values={'org_name': org_name, 'theme_color': theme_color_input,
                             'contact_note': contact_note},
            )

        # Name what actually changed. This action repaints every screen for
        # every member of the institution, and "Branding updated." was
        # indistinguishable from a logo upload that silently didn't attach.
        changes = []
        if org_settings.org_name != org_name:
            changes.append(f'name is now "{org_name}"')
        if (org_settings.contact_note or '') != contact_note:
            changes.append('contact line updated' if contact_note else 'contact line cleared')
        if org_settings.theme_color != normalized_color:
            changes.append(f'accent colour is now {normalized_color}' if normalized_color
                           else 'accent colour is back to the department indigo')

        org_settings.org_name = org_name
        org_settings.contact_note = contact_note or None
        org_settings.theme_color = normalized_color
        if new_logo_data:
            org_settings.logo_data = new_logo_data
            org_settings.logo_content_type = new_logo_content_type
            org_settings.logo_updated_at = datetime.utcnow()
            changes.append('logo replaced')
        elif remove_logo:
            org_settings.logo_data = None
            org_settings.logo_content_type = None
            org_settings.logo_updated_at = None
            changes.append('logo removed')
        db.session.commit()
        if changes:
            summary = changes[0][0].upper() + changes[0][1:]
            if len(changes) > 1:
                summary = '; '.join(changes)
                summary = summary[0].upper() + summary[1:]
            flash(f'{summary}. Everyone sees this on their next page load.', 'success')
        else:
            flash('Nothing changed — the branding is already set that way.', 'info')
        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', org_settings=org_settings, form_values=None)


# ---- Desk check-out ----------------------------------------------------------
#
# The missing half of the stated product purpose. Until now the librarian could
# check books *in* and never *out*: borrowing existed only at
# routes/member.py:borrow_book, so a student at the counter without a phone --
# or without an account they can get into -- could not borrow at all.

@bp.route('/checkout', methods=['GET'])
def checkout():
    member_q = request.args.get('member', '').strip()
    book_q = request.args.get('book', '').strip()

    members = []
    if member_q:
        like = f'%{member_q}%'
        members = User.query.filter(
            User.is_admin.is_(False),
            db.or_(User.username.ilike(like), User.email.ilike(like)),
        ).order_by(User.username).limit(10).all()

    member = None
    member_id = request.args.get('member_id', type=int)
    if member_id:
        member = User.query.filter_by(id=member_id, is_admin=False).first()

    books = []
    if book_q:
        like = f'%{book_q}%'
        books = Book.query.filter(
            db.or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like))
        ).order_by(Book.title).limit(10).all()

    # Everything the librarian needs to judge a loan before making it, computed
    # per candidate book rather than discovered after the POST.
    book_states = {}
    if member and books:
        held = {b.book_id for b in Borrowing.query.filter_by(
            user_id=member.id, status='active').all()}
        for b in books:
            book_states[b.id] = _checkout_block(member, b, held)

    return render_template(
        'admin/checkout.html',
        member_q=member_q, book_q=book_q,
        members=members, member=member, books=books,
        book_states=book_states,
        member_blocked=member.borrow_blocked_reason if member else None,
    )


def _checkout_block(member, book, held_book_ids):
    """Why this member can't be issued this copy right now, or None.

    Deliberately mirrors the member-side rules rather than relaxing them for
    the desk. A librarian override would need an audit trail to be honest
    about who bypassed a limit and why, and this app has none -- so the answer
    to "the rule is in the way" is to check something in, not to route around
    the rule invisibly.
    """
    if book.id in held_book_ids:
        return f'{member.username} already has a copy of this out.'
    if book.available_quantity < 1:
        return 'No copies are on the shelf.'
    # A queue exists and this member is not the one it is being held for.
    next_in_line = Reservation.get_active_reservation(book.id)
    if next_in_line and next_in_line.user_id != member.id:
        return (f'Reserved for {next_in_line.user.username}, who is next in line. '
                'Run Process Reservations, or pick another copy.')
    return None


@bp.route('/checkout', methods=['POST'])
def checkout_issue():
    member_id = request.form.get('member_id', type=int)
    book_id = request.form.get('book_id', type=int)
    member = User.query.filter_by(id=member_id, is_admin=False).first()
    book = Book.query.get(book_id) if book_id else None
    if member is None or book is None:
        flash('Pick a member and a book first.', 'warning')
        return redirect(url_for('admin.checkout'))

    back = url_for('admin.checkout', member_id=member.id,
                   book=request.form.get('book_q', '') or None)

    # The account-level rules (5-loan ceiling, 3-overdue block), in the member's
    # own words -- the same string their catalogue shows them.
    blocked = member.borrow_blocked_reason
    if blocked:
        flash(f'{member.username} can\'t borrow right now — {blocked}', 'warning')
        return redirect(back)

    held = {b.book_id for b in Borrowing.query.filter_by(
        user_id=member.id, status='active').all()}
    per_book = _checkout_block(member, book, held)
    if per_book:
        flash(per_book, 'warning')
        return redirect(back)

    # Atomic decrement, same race-safe pattern as the member borrow path: two
    # desks (or a desk and a phone) must not hand out the same last copy.
    updated = Book.query.filter(
        Book.id == book.id, Book.available_quantity > 0
    ).update({Book.available_quantity: Book.available_quantity - 1},
             synchronize_session=False)
    if not updated:
        db.session.rollback()
        flash(f'"{book.title}" was taken by someone else a moment ago.', 'warning')
        return redirect(back)

    loan_days = current_app.config['LOAN_PERIOD_DAYS']
    now = datetime.utcnow()
    loan = Borrowing(user_id=member.id, book_id=book.id,
                     due_date=now + timedelta(days=loan_days))
    db.session.add(loan)

    # If this member was the one the queue was holding it for, this loan *is*
    # the fulfilment -- otherwise the hold would sit active forever against a
    # copy they are now carrying.
    hold = Reservation.get_active_reservation(book.id)
    if hold and hold.user_id == member.id:
        hold.status = 'fulfilled'

    Notification.push(
        member.id, 'checked_out',
        f'"{book.title}" is checked out to you',
        f'Issued at the desk. Due back '
        f'{to_local(loan.due_date).strftime("%b %d, %Y")}.',
        'member.borrowing_history',
        f'checked_out:{book.id}:{now.isoformat(timespec="seconds")}',
    )
    db.session.commit()

    flash(f'"{book.title}" checked out to {member.username}. '
          f'Due back {to_local(loan.due_date).strftime("%b %d, %Y")}.', 'success')
    return redirect(url_for('admin.checkout', member_id=member.id))
