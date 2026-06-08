from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Book, User, Borrowing, Reservation
from datetime import datetime, timedelta

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.before_request
@login_required
def restrict_to_admins():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('member.dashboard'))


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
    per_page = 20
    search = request.args.get('search', '').strip()

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
    books_pagination = query.order_by(Book.title).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('admin/books.html', pagination=books_pagination, search=search)


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

    if not all([title, author, isbn]):
        flash('Title, Author, and ISBN are required.', 'warning')
        return redirect(url_for('admin.books'))

    existing = Book.query.filter_by(isbn=isbn).first()
    if existing:
        flash(f'A book with ISBN {isbn} already exists ({existing.title}).', 'warning')
        return redirect(url_for('admin.books'))

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
        book.title = request.form.get('title', '').strip()
        book.author = request.form.get('author', '').strip()
        book.isbn = request.form.get('isbn', '').strip()
        book.category = request.form.get('category', '').strip()
        book.publisher = request.form.get('publisher', '').strip()
        book.publication_year = request.form.get('publication_year', type=int)
        book.description = request.form.get('description', '').strip()

        new_quantity = request.form.get('quantity', 1, type=int)
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
    db.session.delete(book)
    db.session.commit()
    flash(f'Book "{book.title}" deleted.', 'success')
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
    now = datetime.utcnow()
    return render_template(
        'admin/members.html',
        pagination=members_pagination,
        search=search,
        now=now,
    )


@bp.route('/members/<int:id>')
def member_detail(id):
    member = User.query.get_or_404(id)
    if member.is_admin:
        flash('Invalid member.', 'danger')
        return redirect(url_for('admin.members'))
    borrowings = Borrowing.query.options(
        db.joinedload(Borrowing.book)
    ).filter_by(user_id=id).order_by(Borrowing.borrow_date.desc()).all()
    reservations = Reservation.query.options(
        db.joinedload(Reservation.book)
    ).filter_by(user_id=id).order_by(Reservation.reservation_date.desc()).all()
    now = datetime.utcnow()
    return render_template(
        'admin/member_detail.html',
        member=member,
        borrowings=borrowings,
        reservations=reservations,
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
    # Cancel active reservations
    Reservation.query.filter_by(user_id=id, status='active').update({'status': 'cancelled'})
    db.session.delete(member)
    db.session.commit()
    flash(f'Member "{member.username}" deleted.', 'success')
    return redirect(url_for('admin.members'))


@bp.route('/borrowing-history')
def borrowing_history():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    filter_status = request.args.get('status', '').strip()

    query = Borrowing.query.options(
        db.joinedload(Borrowing.user),
        db.joinedload(Borrowing.book)
    )
    if filter_status:
        query = query.filter(Borrowing.status == filter_status)
    history_pagination = query.order_by(Borrowing.borrow_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    now = datetime.utcnow()
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
    # Expire overdue reservations
    expired = Reservation.query.filter(
        Reservation.expiration_date < now,
        Reservation.status == 'active'
    ).all()
    for r in expired:
        r.expire()

    # Fulfill reservations when books become available
    available_books = Book.query.filter(Book.available_quantity > 0).all()
    fulfilled_count = 0
    for book in available_books:
        active_reservation = Reservation.get_active_reservation(book.id)
        if active_reservation:
            active_reservation.fulfill()
            book.available_quantity -= 1
            borrowing = Borrowing(
                user_id=active_reservation.user_id,
                book_id=book.id,
                due_date=now + timedelta(days=14)
            )
            db.session.add(borrowing)
            db.session.commit()
            fulfilled_count += 1

    msg = f'Checked reservations: {len(expired)} expired, {fulfilled_count} fulfilled.'
    flash(msg, 'info')
    return redirect(url_for('admin.dashboard'))
