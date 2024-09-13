from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Book, Borrowing
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
            books = Book.query.filter(Book.isbn == search_term).all()
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
    if book.quantity > 0:
        borrowing = Borrowing(user_id=current_user.id, book_id=book_id, due_date=datetime.utcnow() + timedelta(days=14))
        book.quantity -= 1
        db.session.add(borrowing)
        db.session.commit()
        flash('Book borrowed successfully.')
    else:
        flash('This book is currently unavailable.')
    return redirect(url_for('member.search'))

@bp.route('/history')
@login_required
def borrowing_history():
    borrowings = Borrowing.query.filter_by(user_id=current_user.id).order_by(Borrowing.borrow_date.desc()).all()
    return render_template('member/history.html', borrowings=borrowings)
