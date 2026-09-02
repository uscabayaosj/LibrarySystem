"""Guards against N+1 regressions on the member (phone-first) screens.

Several display properties issue their own query, and templates read them
more than once per row -- the dashboard once asked for renew_blocked_reason
three times per loan (can_renew, the branch, then the output), turning five
loans into fifteen identical SELECTs. models.py memoizes them; these tests
assert the counts stay flat as the number of rows grows, which is the actual
property we care about and which a fixed budget wouldn't catch.
"""
from datetime import datetime, timedelta

import pytest
from models import User, Book, Borrowing, Reservation
from tests.conftest import login


def _add_loans(db, member, count):
    """Add `count` more active loans, each with a competing reservation from
    another member so renew_blocked_reason has to do its lookup. Safe to call
    repeatedly -- titles and ISBNs are keyed off what already exists."""
    rival = User.query.filter_by(username='rival').first()
    if rival is None:
        rival = User(username='rival', email='rival@example.com')
        rival.set_password('rivalpass')
        db.session.add(rival)
        db.session.commit()

    stamp = datetime.utcnow()
    start = Book.query.count()

    for i in range(start, start + count):
        book = Book(title=f'Book {i}', author=f'Author {i}',
                    isbn=f'{i:013d}', category='Fiction',
                    quantity=2, available_quantity=1)
        db.session.add(book)
        db.session.flush()
        db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                                 due_date=stamp + timedelta(days=7),
                                 status='active'))
        db.session.add(Reservation(user_id=rival.id, book_id=book.id,
                                   reservation_date=stamp,
                                   expiration_date=stamp + timedelta(days=3),
                                   status='active'))
    db.session.commit()


@pytest.mark.parametrize('path', ['/dashboard', '/history'])
def test_loan_screens_do_not_scale_queries_with_loan_count(
        client, db, member, count_queries, path):
    """Doubling the number of loans must not increase the query count."""
    login(client, 'member', 'memberpass')

    _add_loans(db, member, count=2)
    count_queries.n = 0
    assert client.get(path).status_code == 200
    with_two = count_queries.n

    _add_loans(db, member, count=4)   # now six loans on the page
    count_queries.n = 0
    assert client.get(path).status_code == 200
    with_six = count_queries.n

    assert with_six == with_two, (
        f'{path} issued {with_two} queries for 2 loans but {with_six} for 6 -- '
        'a per-row query has crept back in. Check that templates read the '
        'memoized model properties rather than re-deriving per row.'
    )


def test_reservations_screen_does_not_scale_queries_with_queue_count(
        client, db, member, count_queries):
    """Reservations are uncapped, so per-row queries here are unbounded."""
    login(client, 'member', 'memberpass')

    def add_reservations(count):
        stamp = datetime.utcnow()
        start = Book.query.count()
        for i in range(start, start + count):
            book = Book(title=f'Held {i}', author='Author', isbn=f'{i:013d}',
                        quantity=1, available_quantity=0)
            db.session.add(book)
            db.session.flush()
            db.session.add(Reservation(user_id=member.id, book_id=book.id,
                                       reservation_date=stamp,
                                       expiration_date=stamp + timedelta(days=3),
                                       status='active'))
        db.session.commit()

    add_reservations(2)
    count_queries.n = 0
    assert client.get('/reservations').status_code == 200
    with_two = count_queries.n

    add_reservations(8)   # now ten holds
    count_queries.n = 0
    assert client.get('/reservations').status_code == 200
    with_ten = count_queries.n

    assert with_ten == with_two, (
        f'/reservations issued {with_two} queries for 2 holds but {with_ten} '
        'for 10 -- queue_position/queue_length are querying per row again.'
    )


def test_renewing_invalidates_the_memoized_block_reason(db, member, book):
    """Memoization must not survive a change to the loan itself."""
    from datetime import datetime
    loan = Borrowing(user_id=member.id, book_id=book.id,
                     due_date=datetime.utcnow() - timedelta(days=1),
                     status='active')
    db.session.add(loan)
    db.session.commit()

    # Overdue: blocked, and the reason is now cached on the instance.
    assert loan.renew_blocked_reason is not None
    assert loan.can_renew is False

    # Returning it changes the answer; the cache must not hide that.
    loan.mark_returned()
    assert loan.renew_blocked_reason is None


def test_shell_counts_are_one_query(db, member, count_queries):
    """The four numbers every member page needs for its chrome -- tab-bar
    badges for loans and holds, the bell's unread count, the home-screen
    overdue badge -- come from one round trip, not four. On a serverless
    host every round trip is paid in full, so this is the difference
    between a snappy tab bar and a laggy one."""
    member.id   # the fixture's commit expired the row; reload it off the clock
    count_queries.n = 0
    member.active_borrowings
    member.active_reservations_count
    member.unread_notices
    member.overdue_borrowings
    assert count_queries.n == 1, (
        f'reading the four shell counts issued {count_queries.n} queries; '
        'they should share a single SELECT'
    )


def test_borrowing_invalidates_shell_counts(db, member, book):
    from models import Notification
    assert member.active_borrowings == 0
    db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                             due_date=datetime.utcnow() + timedelta(days=7),
                             status='active'))
    db.session.commit()
    member._invalidate_borrow_state()
    assert member.active_borrowings == 1
