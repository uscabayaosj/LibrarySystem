from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, abort
from flask_login import login_required, current_user
from models import db, Book, Borrowing, Reservation
from datetime import datetime, timedelta
from calendar_export import build_ics
from localtime import to_local

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
    # Completed events only -- showing open loans here would just repeat the
    # "Currently Borrowed" panel beside it.
    recent_returns = Borrowing.query.options(
        db.joinedload(Borrowing.book)
    ).filter_by(user_id=current_user.id, status='returned').order_by(
        Borrowing.return_date.desc()
    ).limit(4).all()
    return render_template(
        'member/dashboard.html',
        active_borrowings=active_borrowings,
        overdue_count=len(overdue_items),
        overdue_items=overdue_items,
        active_reservations=active_reservations,
        recent_returns=recent_returns,
        now=now,
    )


@bp.route('/search')
@login_required
def search():
    search_term = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Book.query
    if search_term:
        like = f'%{search_term}%'
        filters = {
            'all': db.or_(
                Book.title.ilike(like), Book.author.ilike(like),
                Book.isbn.ilike(like), Book.category.ilike(like),
            ),
            'title': Book.title.ilike(like),
            'author': Book.author.ilike(like),
            'isbn': Book.isbn.ilike(like),
            'category': Book.category.ilike(like),
        }
        book_filter = filters.get(search_type)
        if book_filter is None:
            search_type = 'all'
            book_filter = filters['all']
        query = query.filter(book_filter)

    pagination = query.order_by(Book.title).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # What the viewer already holds, so the cards don't offer an action that
    # the server is guaranteed to reject.
    my_loans = {
        b.book_id: b for b in Borrowing.query.filter_by(
            user_id=current_user.id, status='active'
        ).all()
    }
    my_reservations = {
        r.book_id: r for r in Reservation.query.filter_by(
            user_id=current_user.id, status='active'
        ).all()
    }

    return render_template(
        'member/search.html',
        pagination=pagination,
        books=pagination.items,
        search_term=search_term,
        search_type=search_type,
        my_loans=my_loans,
        my_reservations=my_reservations,
    )


@bp.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    now = datetime.utcnow()

    # Prevent borrowing a second copy of a title the member already holds.
    already = Borrowing.query.filter_by(
        user_id=current_user.id, book_id=book_id, status='active'
    ).first()
    if already:
        flash(f'You already have "{book.title}" borrowed.', 'info')
        return redirect(url_for('member.search', q=book.title))

    active_count = Borrowing.query.filter_by(
        user_id=current_user.id, status='active'
    ).count()
    if active_count >= current_app.config['MAX_ACTIVE_LOANS']:
        flash('You have reached the maximum number of borrowed books. '
              'Please return some before borrowing more.', 'warning')
        return redirect(url_for('member.search', q=book.title))

    overdue = Borrowing.query.filter(
        Borrowing.user_id == current_user.id,
        Borrowing.status == 'active',
        Borrowing.due_date < now
    ).count()
    if overdue >= current_app.config['MAX_OVERDUE_BEFORE_BLOCK']:
        flash('You have too many overdue books. Please return them first.', 'warning')
        return redirect(url_for('member.search', q=book.title))

    # Atomic, race-safe decrement: only succeeds if a copy is still available.
    loan_days = current_app.config['LOAN_PERIOD_DAYS']
    updated = Book.query.filter(
        Book.id == book_id, Book.available_quantity > 0
    ).update(
        {Book.available_quantity: Book.available_quantity - 1},
        synchronize_session=False,
    )
    if not updated:
        db.session.rollback()
        flash(f'"{book.title}" is not available for borrowing.', 'warning')
        return redirect(url_for('member.search', q=book.title))

    borrowing = Borrowing(
        user_id=current_user.id,
        book_id=book_id,
        due_date=now + timedelta(days=loan_days),
    )
    db.session.add(borrowing)
    db.session.commit()
    flash(f'"{book.title}" borrowed successfully! Due in {loan_days} days.', 'success')
    return redirect(url_for('member.search', q=book.title))


@bp.route('/reserve/<int:book_id>', methods=['POST'])
@login_required
def reserve_book(book_id):
    book = Book.query.get_or_404(book_id)
    hold_days = current_app.config['RESERVATION_HOLD_DAYS']
    existing = Reservation.query.filter_by(
        user_id=current_user.id, book_id=book_id, status='active'
    ).first()
    if existing:
        flash('You already have an active reservation for this book.', 'info')
    elif book.can_reserve():
        reservation = Reservation(
            user_id=current_user.id,
            book_id=book_id,
            expiration_date=datetime.utcnow() + timedelta(days=hold_days)
        )
        db.session.add(reservation)
        db.session.commit()
        flash(f'"{book.title}" reserved! You have {hold_days} days to claim it.', 'success')
    else:
        flash('This book cannot be reserved at the moment.', 'warning')
    return redirect(url_for('member.search', q=book.title))


_RENEW_REDIRECTS = {
    'dashboard': lambda: url_for('member.dashboard'),
    'history': lambda: url_for('member.borrowing_history'),
}


@bp.route('/renew/<int:borrowing_id>', methods=['POST'])
@login_required
def renew_borrowing(borrowing_id):
    borrowing = Borrowing.query.get_or_404(borrowing_id)
    # Only two known redirect targets are ever accepted -- this is a closed
    # set, not user-controlled input, so it can't become an open redirect.
    destination = _RENEW_REDIRECTS.get(
        request.form.get('next'), _RENEW_REDIRECTS['history']
    )()

    if borrowing.user_id != current_user.id:
        flash('You do not have permission to renew this loan.', 'danger')
        return redirect(destination)

    if not borrowing.can_renew:
        flash(borrowing.renew_blocked_reason or 'This loan cannot be renewed.', 'warning')
        return redirect(destination)

    borrowing.renew()
    flash(
        f'"{borrowing.book.title}" renewed — now due '
        f'{borrowing.due_date.strftime("%b %d, %Y")}.',
        'success',
    )
    return redirect(destination)


@bp.route('/loans/<int:borrowing_id>/calendar.ics')
@login_required
def loan_calendar(borrowing_id):
    """Downloadable due-date reminder. This is the practical shape a
    'reminder' takes without any push-notification infrastructure: the
    phone's own Calendar app gets an event with a built-in alarm the day
    before the book is due."""
    borrowing = Borrowing.query.options(db.joinedload(Borrowing.book)).get_or_404(borrowing_id)
    if borrowing.user_id != current_user.id:
        abort(403)
    if borrowing.status != 'active':
        flash('This loan has already been returned.', 'info')
        return redirect(url_for('member.borrowing_history'))

    ics = build_ics(
        uid=f'loan-{borrowing.id}@library-system',
        summary=f'Return "{borrowing.book.title}"',
        description=(
            f'"{borrowing.book.title}" by {borrowing.book.author} is due back '
            f'at the Anthropology Department library.'
        ),
        event_date=to_local(borrowing.due_date),
        reminder_days_before=1,
        alarm_description=f'"{borrowing.book.title}" is due tomorrow',
    )
    return Response(
        ics,
        mimetype='text/calendar',
        headers={
            'Content-Disposition': f'attachment; filename="loan-{borrowing.id}.ics"',
        },
    )


@bp.route('/history')
@login_required
def borrowing_history():
    # Paginated rather than .all(): a long-standing member accumulates loans
    # without limit, and this is the phone-first screen -- rendering every
    # record ever borrowed sends a page that grows forever over mobile data.
    page = request.args.get('page', 1, type=int)
    pagination = Borrowing.query.options(
        db.joinedload(Borrowing.book)
    ).filter_by(user_id=current_user.id).order_by(
        Borrowing.borrow_date.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    return render_template(
        'member/history.html',
        borrowings=pagination.items,
        pagination=pagination,
        now=datetime.utcnow(),
    )


@bp.route('/reservations')
@login_required
def reservations():
    active_reservations = Reservation.query.options(
        db.joinedload(Reservation.book)
    ).filter_by(user_id=current_user.id, status='active').order_by(
        Reservation.reservation_date.desc()
    ).all()
    return render_template(
        'member/reservations.html',
        reservations=active_reservations,
        now=datetime.utcnow(),
    )


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


@bp.route('/reservations/<int:reservation_id>/calendar.ics')
@login_required
def reservation_calendar(reservation_id):
    """Downloadable expiry reminder, the reservation-queue counterpart to
    loan_calendar()."""
    reservation = Reservation.query.options(
        db.joinedload(Reservation.book)
    ).get_or_404(reservation_id)
    if reservation.user_id != current_user.id:
        abort(403)
    if reservation.status != 'active':
        flash('This reservation is no longer active.', 'info')
        return redirect(url_for('member.reservations'))

    ics = build_ics(
        uid=f'reservation-{reservation.id}@library-system',
        summary=f'Claim "{reservation.book.title}"',
        description=(
            f'Your reservation for "{reservation.book.title}" by '
            f'{reservation.book.author} expires today -- claim it at the '
            f'Anthropology Department library or it will go to the next '
            f'person in the queue.'
        ),
        event_date=to_local(reservation.expiration_date),
        reminder_days_before=1,
        alarm_description=f'Your hold on "{reservation.book.title}" expires tomorrow',
    )
    return Response(
        ics,
        mimetype='text/calendar',
        headers={
            'Content-Disposition': f'attachment; filename="reservation-{reservation.id}.ics"',
        },
    )
