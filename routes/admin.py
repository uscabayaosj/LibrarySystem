from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Book, User, Borrowing
from datetime import datetime
import logging

bp = Blueprint('admin', __name__, url_prefix='/admin')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@bp.before_request
@login_required
def restrict_to_admins():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('member.dashboard'))

@bp.route('/dashboard')
def dashboard():
    return render_template('admin/dashboard.html')

@bp.route('/books', methods=['GET', 'POST'])
def books():
    if request.method == 'POST':
        try:
            title = request.form['title']
            author = request.form['author']
            isbn = request.form['isbn']
            category = request.form['category']
            quantity = int(request.form['quantity'])
            
            if not all([title, author, isbn, category, quantity]):
                raise ValueError("All fields are required")
            
            book = Book(title=title, author=author, isbn=isbn, category=category, quantity=quantity, available_quantity=quantity)
            db.session.add(book)
            db.session.commit()
            flash('Book added successfully.')
            logger.info(f"Book added: {title} by {author}")
            return redirect(url_for('admin.books'))
        except ValueError as e:
            flash(str(e))
            logger.error(f"Error adding book: {str(e)}")
        except Exception as e:
            flash('An error occurred while adding the book.')
            logger.error(f"Unexpected error adding book: {str(e)}")
    
    books = Book.query.all()
    return render_template('admin/books.html', books=books)

@bp.route('/books/<int:id>/edit', methods=['GET', 'POST'])
def edit_book(id):
    book = Book.query.get_or_404(id)
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.isbn = request.form['isbn']
        book.category = request.form['category']
        book.quantity = int(request.form['quantity'])
        db.session.commit()
        flash('Book updated successfully.')
        return redirect(url_for('admin.books'))
    return render_template('admin/edit_book.html', book=book)

@bp.route('/books/<int:id>/delete', methods=['POST'])
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully.')
    return redirect(url_for('admin.books'))

@bp.route('/members')
def members():
    members = User.query.filter_by(is_admin=False).all()
    return render_template('admin/members.html', members=members)

@bp.route('/borrowing-history')
def borrowing_history():
    borrowings = Borrowing.query.order_by(Borrowing.borrow_date.desc()).all()
    return render_template('admin/borrowing_history.html', borrowings=borrowings)
