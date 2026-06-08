from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Book, Borrowing, Reservation
from datetime import datetime, timedelta

bp = Blueprint('member', __name__)


@bp.route('/dashboard')
@login_required
def dashboard():
    now = datetime.utcnow()
    active_borrowings = Borrowing.query.options(
        db.joinedload(Borrowing.book)
    ).filter_by(user_id=current_user.id, status='active').all()
    overdue_items = [b for b in active_borrowings if b.due_date < now]
    active_reservations = Reservation.query.options(
        db.joinedload(Reservation.book)
    ).filter_by(user_id=current_user.id, status='active').count()
    recent_history = Borrowing.query.options(
        db.joinedload(Borrowing.book)
    ).filter_by(user_id=current_user.id).order_by(
        Borrowing.borrow_date.desc()
    ).limit(5).all()
    return render_template(
        'member/dashboard.html',
        active_borrowings=active_borrowings,
        overdue_count=len(overdue_items),
        overdue_items=overdue_items,
        active_reservations=active_reservations,
        recent_history=recent_history,
        now=now,
    )


@bp.route('/search')
@login_required
def search():
    search_term = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'title')

    books = []
    if search_term:
        filters = {
            'title': Book.title.ilike(f'%{search_term}%'),
            'author': Book.author.ilike(f'%{search_term}%'),
            'isbn': Book.isbn.ilike(f'%{search_term}%'),
            'category': Book.category.ilike(f'%{search_term}%'),
        }
        book_filter = filters.get(search_type)
        if book_filter is not None:
            books = Book.query.filter(book_filter).order_by(Book.title).all()
        else:
            flash('Invalid search type.', 'warning')
    else:
        # Show all books when no search term
        books = Book.query.order_by(Book.title).all()

    return render_template(
        'member/search.html',
        books=books,
        search_term=search_term,
        search_type=search_type,
    )


@bp.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.is_available():
        # Check for overdue items
        overdue = Borrowing.query.filter(
            Borrowing.user_id == current_user.id,
            Borrowing.status == 'active',
            Borrowing.due_date < datetime.utcnow()
        ).count()
        if overdue >= 3:
            flash('You have too many overdue books. Please return them first.', 'warning')
            return redirect(url_for('member.search', q=book.title))

        borrowing = Borrowing(
            user_id=current_user.id,
            book_id=book_id,
            due_date=datetime.utcnow() + timedelta(days=14)
        )
        book.available_quantity -= 1
        db.session.add(borrowing)
        db.session.commit()
        flash(f'"{book.title}" borrowed successfully! Due in 14 days.', 'success')
    else:
        flash(f'"{book.title}" is not available for borrowing.', 'warning')
    return redirect(url_for('member.search', q=book.title))


@bp.route('/reserve/<int:book_id>', methods=['POST'])
@login_required
def reserve_book(book_id):
    book = Book.query.get_or_404(book_id)
    existing = Reservation.query.filter_by(
        user_id=current_user.id, book_id=book_id, status='active'
    ).first()
    if existing:
        flash('You already have an active reservation for this book.', 'info')
    elif book.can_reserve():
        reservation = Reservation(
            user_id=current_user.id,
            book_id=book_id,
            expiration_date=datetime.utcnow() + timedelta(days=3)
        )
        db.session.add(reservation)
        db.session.commit()
        flash(f'"{book.title}" reserved! You have 3 days to claim it.', 'success')
    else:
        flash('This book cannot be reserved at the moment.', 'warning')
    return redirect(url_for('member.search', q=book.title))


@bp.route('/history')
@login_required
def borrowing_history():
    borrowings = Borrowing.query.options(
        db.joinedload(Borrowing.book)
    ).filter_by(user_id=current_user.id).order_by(
        Borrowing.borrow_date.desc()
    ).all()
    return render_template('member/history.html', borrowings=borrowings, now=datetime.utcnow())


@bp.route('/reservations')
@login_required
def reservations():
    active_reservations = Reservation.query.options(
        db.joinedload(Reservation.book)
    ).filter_by(user_id=current_user.id, status='active').order_by(
        Reservation.reservation_date.desc()
    ).all()
    return render_template('member/reservations.html', reservations=active_reservations)


@bp.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id:
        flash('You do not have permission to cancel this reservation.', 'danger')
        return redirect(url_for('member.reservations'))
    reservation.status = 'cancelled'
    db.session.commit()
    flash('Reservation cancelled.', 'success')
    return redirect(url_for('member.reservations'))
