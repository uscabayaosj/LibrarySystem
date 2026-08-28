"""Hardening guards: over-length input, and unbounded record lists.

The length checks matter specifically because SQLite does not enforce
VARCHAR limits and Postgres does. Without these, an over-long title is
accepted in development and in this very test suite, then fails in
production with `DataError: value too long for type character varying(200)`
and an unhandled 500. The tests assert the app rejects it *before* it
reaches the database, so the behaviour is the same on both backends.
"""
from datetime import datetime, timedelta

import pytest

from models import Book, User, Borrowing
from validation import max_length
from tests.conftest import login


# ---- Over-length input is rejected, not stored -------------------------------

@pytest.mark.parametrize('field,payload_len', [
    ('title', 500),
    ('author', 300),
    ('isbn', 40),
    ('category', 200),
    ('publisher', 300),
])
def test_add_book_rejects_over_length_field(client, db, admin, field, payload_len):
    login(client, 'admin', 'adminpass')
    form = {'title': 'Fine Title', 'author': 'Fine Author',
            'isbn': '9780000000001', 'category': 'Fiction',
            'publisher': 'Fine Publisher', 'quantity': '1'}
    form[field] = 'x' * payload_len

    resp = client.post('/admin/books/add', data=form, follow_redirects=True)

    assert resp.status_code == 200
    assert Book.query.count() == 0, f'over-length {field} was stored'
    limit = max_length(Book, field)
    assert f'must be {limit} characters or fewer' in resp.get_data(as_text=True)


def test_add_book_still_accepts_valid_input(client, db, admin):
    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/books/add', data={
        'title': 'A Perfectly Normal Book', 'author': 'Real Author',
        'isbn': '9780000000002', 'category': 'Fiction',
        'publisher': 'A Publisher', 'quantity': '2',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert Book.query.count() == 1


def test_register_rejects_over_length_username(client, db):
    resp = client.post('/register', data={
        'username': 'u' * 300, 'email': 'someone@example.com',
        'password': 'password123',
    }, follow_redirects=True)
    assert User.query.filter_by(email='someone@example.com').first() is None
    limit = max_length(User, 'username')
    assert f'must be {limit} characters or fewer' in resp.get_data(as_text=True)


def test_every_declared_limit_is_discoverable():
    """The template `maxlength` and the server check both read these, so a
    None here would silently disable both."""
    for field in ('title', 'author', 'isbn', 'category', 'publisher'):
        assert max_length(Book, field), f'Book.{field} has no declared length'
    for field in ('username', 'email'):
        assert max_length(User, field), f'User.{field} has no declared length'


# ---- Record lists stay bounded ----------------------------------------------

def _give_loans(db, member, count):
    stamp = datetime.utcnow()
    start = Book.query.count()
    for i in range(start, start + count):
        book = Book(title=f'Book {i}', author='Author', isbn=f'{i:013d}',
                    quantity=1, available_quantity=0)
        db.session.add(book)
        db.session.flush()
        db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                                 due_date=stamp - timedelta(days=40),
                                 status='returned',
                                 return_date=stamp - timedelta(days=35)))
    db.session.commit()


# Both sizes below deliberately exceed the largest per_page on these screens,
# so page one is already full at the smaller size. Comparing a full page to a
# full page isolates the property under test -- payload must not track the
# number of records -- rather than measuring a half-empty first page.
SMALL_HISTORY = 60
LARGE_HISTORY = 400

# Between two full-page sizes the only legitimate growth is digit width in
# the totals and the pagination nav gaining its gap form. Measured: +277
# bytes from 60->400 loans, +26 from 400->1200. The slack is absolute, not
# relative: a percentage of a ~35KB page (~3.5KB at 10%) is wide enough to
# hide a genuine per-record leak of several bytes x hundreds of records,
# which is precisely the bug class this test exists to catch.
PAYLOAD_SLACK_BYTES = 600


def _loan_rows(response):
    """Loan rows rendered on the page: each carries one Borrowed cell."""
    return response.get_data(as_text=True).count('data-label="Borrowed"')


def test_member_history_payload_stays_bounded(client, db, member):
    """A member accumulates loans forever; the page must not grow with them."""
    login(client, 'member', 'memberpass')

    _give_loans(db, member, SMALL_HISTORY)
    resp_small = client.get('/history')
    small, rows_small = len(resp_small.data), _loan_rows(resp_small)

    _give_loans(db, member, LARGE_HISTORY - SMALL_HISTORY)
    resp_large = client.get('/history')
    large, rows_large = len(resp_large.data), _loan_rows(resp_large)

    # Structure: one page of rows, identical at both sizes, far below the
    # record count -- the direct check that pagination is actually applied.
    assert rows_small == rows_large, (
        f'/history rendered {rows_small} rows at {SMALL_HISTORY} loans but '
        f'{rows_large} at {LARGE_HISTORY} -- page size is tracking the data.'
    )
    assert rows_large < LARGE_HISTORY / 4, (
        f'/history rendered {rows_large} rows -- not paginated.'
    )
    # Payload: bounded by an absolute slack sized from measured legitimate
    # growth, so even a small per-record leak fails loudly.
    assert large - small <= PAYLOAD_SLACK_BYTES, (
        f'/history grew {large - small} bytes going from {SMALL_HISTORY} to '
        f'{LARGE_HISTORY} loans (legitimate growth measures <300); '
        'something on the page scales with record count.'
    )


def test_admin_member_detail_payload_stays_bounded(client, db, admin, member):
    login(client, 'admin', 'adminpass')

    _give_loans(db, member, SMALL_HISTORY)
    resp_small = client.get(f'/admin/members/{member.id}')
    small, rows_small = len(resp_small.data), _loan_rows(resp_small)

    _give_loans(db, member, LARGE_HISTORY - SMALL_HISTORY)
    resp_large = client.get(f'/admin/members/{member.id}')
    large, rows_large = len(resp_large.data), _loan_rows(resp_large)

    assert rows_small == rows_large, (
        f'member_detail rendered {rows_small} rows at {SMALL_HISTORY} loans '
        f'but {rows_large} at {LARGE_HISTORY}.'
    )
    assert rows_large < LARGE_HISTORY / 4, (
        f'member_detail rendered {rows_large} rows -- not paginated.'
    )
    assert large - small <= PAYLOAD_SLACK_BYTES, (
        f'member_detail grew {large - small} bytes going from '
        f'{SMALL_HISTORY} to {LARGE_HISTORY} loans (legitimate growth '
        'measures <300); something on the page scales with record count.'
    )


# ---- Serverless connection pooling ------------------------------------------

def test_engine_recovers_from_a_connection_closed_by_the_server():
    """A pooled connection whose far end hung up must not surface as a 500.

    Neon suspends idle computes and its pooler drops idle connections, while
    the Vercel instance holding the pool stays warm and reuses it. Without
    pool_pre_ping the next request gets a dead connection and dies with
    `OperationalError: SSL connection has been closed unexpectedly`, having
    done nothing wrong -- a page that 500s once after a quiet period and
    works on reload. Simulated here by closing the DBAPI connection directly;
    the dialect differs from production, the mechanism does not.
    """
    import sqlalchemy as sa
    from config import Config

    def survives_a_hangup(**engine_options):
        engine = sa.create_engine('sqlite://', **engine_options)
        with engine.connect() as conn:
            conn.execute(sa.text('SELECT 1'))       # pool one connection
        engine.pool.connect().dbapi_connection.close()   # server hangs up
        try:
            with engine.connect() as conn:
                conn.execute(sa.text('SELECT 1'))
            return True
        except sa.exc.SQLAlchemyError:
            return False

    # The guard is load-bearing, not incidental: without it this same
    # sequence fails.
    assert not survives_a_hangup(pool_pre_ping=False)
    assert survives_a_hangup(**Config.SQLALCHEMY_ENGINE_OPTIONS)


def test_pool_recycles_before_neon_drops_idle_connections():
    """pool_recycle has to stay under the provider's idle timeout, or
    connections reach it first and pre_ping is left doing all the recovering."""
    from config import Config

    recycle = Config.SQLALCHEMY_ENGINE_OPTIONS['pool_recycle']
    assert 0 < recycle < 300
