import os

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, Book, User, Borrowing, Reservation, OrganizationSettings
from datetime import datetime, timedelta
from theming import normalize_hex
from logo_upload import validate_and_save, LogoValidationError
from validation import length_errors

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


def _books_context(page=1, search='', form_values=None, form_errors=None):
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
    pagination = query.order_by(Book.title).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return {
        'pagination': pagination,
        'search': search,
        'form_values': form_values or {},
        'form_errors': form_errors,
    }


@bp.route('/dashboard')
def dashboard():
    now = datetime.utcnow()
    total_books = Book.query.count()
    total_members = User.query.filter_by(is_admin=False).count()
    active_borrowings = Borrowing.query.filter_by(status='active').count()
    overdue_count = Borrowing.query.filter(
        Borrowing.status == 'active',
        Borrowing.due_date < now
    ).count()
    active_reservations = Reservation.query.filter_by(status='active').count()
    available_books = Book.query.filter(Book.available_quantity > 0).count()

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
        now=now,
    )


@bp.route('/books')
def books():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    return render_template('admin/books.html', **_books_context(page, search))


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

    errors = []
    if not all([title, author, isbn]):
        errors.append('Title, Author, and ISBN are required.')
    errors.extend(length_errors(Book, {
        'title': title, 'author': author, 'isbn': isbn,
        'category': category, 'publisher': publisher,
    }))
    if quantity is None or quantity < 1:
        errors.append('Quantity must be at least 1.')
        quantity = 1
    existing = Book.query.filter_by(isbn=isbn).first() if isbn else None
    if existing:
        errors.append(f'A book with ISBN {isbn} already exists ({existing.title}).')

    if errors:
        for msg in errors:
            flash(msg, 'warning')
        return render_template(
            'admin/books.html',
            **_books_context(1, '', form_values=request.form, form_errors=errors)
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
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        new_quantity = request.form.get('quantity', book.quantity, type=int)

        errors = []
        if not all([title, author, isbn]):
            errors.append('Title, Author, and ISBN are required.')
        errors.extend(length_errors(Book, {
            'title': title, 'author': author, 'isbn': isbn,
            'category': request.form.get('category', '').strip(),
            'publisher': request.form.get('publisher', '').strip(),
        }))
        if new_quantity is None or new_quantity < 0:
            errors.append('Quantity cannot be negative.')
            new_quantity = book.quantity
        duplicate = Book.query.filter(Book.isbn == isbn, Book.id != id).first() if isbn else None
        if duplicate:
            errors.append(f'Another book already uses ISBN {isbn} ({duplicate.title}).')

        if errors:
            for msg in errors:
                flash(msg, 'warning')
            return render_template('admin/edit_book.html', book=book)

        book.title = title
        book.author = author
        book.isbn = isbn
        book.category = request.form.get('category', '').strip()
        book.publisher = request.form.get('publisher', '').strip()
        book.publication_year = request.form.get('publication_year', type=int)
        book.description = request.form.get('description', '').strip()

        diff = new_quantity - book.quantity
        book.quantity = new_quantity
        book.available_quantity = max(0, book.available_quantity + diff)
        db.session.commit()
        flash('Book updated successfully.', 'success')
        return redirect(url_for('admin.books'))
    return render_template('admin/edit_book.html', book=book)


@bp.route('/books/<int:id>/delete', methods=['POST'])
def delete_book(id):
    book = Book.query.get_or_404(id)
    active_borrowings = Borrowing.query.filter_by(book_id=id, status='active').count()
    if active_borrowings > 0:
        flash(f'Cannot delete: {active_borrowings} copy(ies) are currently borrowed.', 'warning')
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
    members_pagination = query.order_by(User.username).paginate(
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
            Borrowing.due_date < now,
        ).group_by(Borrowing.user_id).all()
        overdue_counts = dict(rows)

    return render_template(
        'admin/members.html',
        pagination=members_pagination,
        search=search,
        now=now,
        active_counts=active_counts,
        overdue_counts=overdue_counts,
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


@bp.route('/members/<int:id>/delete', methods=['POST'])
def delete_member(id):
    member = User.query.get_or_404(id)
    if member.is_admin:
        flash('Cannot delete admin users.', 'danger')
        return redirect(url_for('admin.members'))
    active_count = Borrowing.query.filter_by(user_id=id, status='active').count()
    if active_count > 0:
        flash(f'Cannot delete: member has {active_count} active borrowing(s).', 'warning')
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

    now = datetime.utcnow()
    query = Borrowing.query.options(
        db.joinedload(Borrowing.user),
        db.joinedload(Borrowing.book)
    )
    if filter_status == 'overdue':
        # Overdue isn't a stored status -- it's active plus a past due date.
        query = query.filter(Borrowing.status == 'active', Borrowing.due_date < now)
    elif filter_status in ('active', 'returned'):
        query = query.filter(Borrowing.status == filter_status)
    else:
        filter_status = ''
    history_pagination = query.order_by(Borrowing.borrow_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template(
        'admin/borrowing_history.html',
        pagination=history_pagination,
        filter_status=filter_status,
        now=now,
    )


@bp.route('/return-book/<int:id>', methods=['POST'])
def return_book(id):
    borrowing = Borrowing.query.get_or_404(id)
    if borrowing.status != 'active':
        flash('This book has already been returned.', 'info')
        return redirect(url_for('admin.borrowing_history'))
    borrowing.mark_returned()
    flash(f'"{borrowing.book.title}" returned by {borrowing.user.username}.', 'success')
    return redirect(url_for('admin.borrowing_history'))


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
    available_books = Book.query.filter(Book.available_quantity > 0).all()
    for book in available_books:
        while book.available_quantity > 0:
            active_reservation = Reservation.get_active_reservation(book.id)
            if not active_reservation:
                break
            active_reservation.status = 'fulfilled'
            book.available_quantity -= 1
            db.session.add(Borrowing(
                user_id=active_reservation.user_id,
                book_id=book.id,
                due_date=now + timedelta(days=loan_days)
            ))
            fulfilled_count += 1

    db.session.commit()
    flash(f'Checked reservations: {len(expired)} expired, {fulfilled_count} fulfilled.', 'info')
    return redirect(url_for('admin.dashboard'))


def _branding_upload_dir():
    return os.path.join(current_app.root_path, 'static', 'uploads', 'branding')


@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    org_settings = OrganizationSettings.get()

    if request.method == 'POST':
        org_name = request.form.get('org_name', '').strip()
        theme_color_input = request.form.get('theme_color', '').strip()
        remove_logo = request.form.get('remove_logo') == 'on'
        logo_file = request.files.get('logo')

        errors = []
        if not org_name:
            errors.append('Organization name is required.')
        elif len(org_name) > 80:
            errors.append('Organization name must be 80 characters or fewer.')

        normalized_color = None
        if theme_color_input:
            normalized_color = normalize_hex(theme_color_input)
            if not normalized_color:
                errors.append('Theme color must be a valid hex color, e.g. #292168.')

        new_logo_filename = None
        if logo_file and logo_file.filename:
            try:
                new_logo_filename = validate_and_save(logo_file, _branding_upload_dir())
            except LogoValidationError as e:
                errors.append(str(e))

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template(
                'admin/settings.html',
                org_settings=org_settings,
                form_values={'org_name': org_name, 'theme_color': theme_color_input},
            )

        org_settings.org_name = org_name
        org_settings.theme_color = normalized_color
        if new_logo_filename:
            org_settings.logo_filename = new_logo_filename
        elif remove_logo:
            org_settings.logo_filename = None
        db.session.commit()
        flash('Branding updated.', 'success')
        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', org_settings=org_settings, form_values=None)
