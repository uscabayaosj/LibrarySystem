from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Book, Borrowing, Reservation
from datetime import datetime, timedelta

bp = Blueprint('member', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('member/dashboard.html')

@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        search_term = request.form['search_term']
        search_type = request.form['search_type']
        
        if search_type == 'title':
            books = Book.query.filter(Book.title.ilike(f'%{search_term}%')).all()
        elif search_type == 'author':
            books = Book.query.filter(Book.author.ilike(f'%{search_term}%')).all()
        elif search_type == 'isbn':
            books = Book.query.filter(Book.isbn.ilike(f'%{search_term}%')).all()
        elif search_type == 'category':
            books = Book.query.filter(Book.category.ilike(f'%{search_term}%')).all()
        else:
            books = []
        
        return render_template('member/search.html', books=books)
    
    return render_template('member/search.html')

@bp.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.is_available():
        borrowing = Borrowing(user_id=current_user.id, book_id=book_id, due_date=datetime.utcnow() + timedelta(days=14))
        book.available_quantity -= 1
        db.session.add(borrowing)
        db.session.commit()
        flash('Book borrowed successfully.')
    else:
        flash('This book is not available for borrowing.')
    return redirect(url_for('member.search'))

@bp.route('/reserve/<int:book_id>', methods=['POST'])
@login_required
def reserve_book(book_id):
    book = Book.query.get_or_404(book_id)
    existing_reservation = Reservation.query.filter_by(user_id=current_user.id, book_id=book_id, status='active').first()
    if existing_reservation:
        flash('You have already reserved this book.')
    elif book.can_reserve():
        reservation = Reservation(user_id=current_user.id, book_id=book_id, expiration_date=datetime.utcnow() + timedelta(days=3))
        db.session.add(reservation)
        db.session.commit()
        flash('Book reserved successfully.')
    else:
        flash('This book cannot be reserved at the moment.')
    return redirect(url_for('member.search'))

@bp.route('/history')
@login_required
def borrowing_history():
    borrowings = Borrowing.query.filter_by(user_id=current_user.id).order_by(Borrowing.borrow_date.desc()).all()
    return render_template('member/history.html', borrowings=borrowings, now=datetime.utcnow())

@bp.route('/reservations')
@login_required
def reservations():
    active_reservations = Reservation.query.filter_by(user_id=current_user.id, status='active').order_by(Reservation.reservation_date.desc()).all()
    return render_template('member/reservations.html', reservations=active_reservations)

@bp.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id:
        flash('You do not have permission to cancel this reservation.')
    else:
        reservation.status = 'cancelled'
        db.session.commit()
        flash('Reservation cancelled successfully.')
    return redirect(url_for('member.reservations'))

@bp.route('/check_reservations')
@login_required
def check_reservations():
    now = datetime.utcnow()
    expired_reservations = Reservation.query.filter(Reservation.expiration_date < now, Reservation.status == 'active').all()
    for reservation in expired_reservations:
        reservation.expire()
    
    available_books = Book.query.filter(Book.available_quantity > 0).all()
    for book in available_books:
        active_reservation = Reservation.get_active_reservation(book.id)
        if active_reservation:
            active_reservation.fulfill()
            book.available_quantity -= 1
            borrowing = Borrowing(user_id=active_reservation.user_id, book_id=book.id, due_date=now + timedelta(days=14))
            db.session.add(borrowing)
            db.session.commit()
            # TODO: Implement notification system to inform user about fulfilled reservation
    
    return redirect(url_for('member.dashboard'))
