"""Tests for the reservation queue-position indicator and expiry labels."""
from datetime import datetime, timedelta

import pytest

import models
from localtime import to_local
from models import Reservation, User
from tests.conftest import login

# A fixed instant, 09:00 in the library's local timezone (see localtime.py) and
# so nowhere near a day boundary in either UTC or local time. Same purpose and
# value as test_regressions.FIXED_UTC_NOW: days_until_expiry compares local
# calendar dates, so it depends on *when* "now" is and not just on the elapsed
# offset. Pinning models.local_now() to this makes those assertions
# deterministic whatever time of day the suite runs at.
FIXED_UTC_NOW = datetime(2026, 1, 10, 1, 0, 0)


@pytest.fixture
def pinned_clock(monkeypatch):
    """Pin the library-local clock that the calendar-day properties read."""
    monkeypatch.setattr(models, 'local_now', lambda: to_local(FIXED_UTC_NOW))
    return FIXED_UTC_NOW


def _reservation(db, user, book, reserved_at, status='active', expires_at=None):
    r = Reservation(
        user_id=user.id, book_id=book.id,
        reservation_date=reserved_at,
        # The default trails reserved_at, which the queue tests build from
        # utcnow() -- fine for them, because queue_position orders on raw
        # timestamps. Pass expires_at explicitly for anything asserting on
        # days_until_expiry or expiry_label: those compare library-local
        # calendar days, and a due date carrying a sub-day offset from the
        # real clock straddles local midnight for part of every day. That is
        # exactly how test_due_today_is_not_reported_as_overdue_zero came to
        # fail for two hours daily before it was pinned.
        expiration_date=reserved_at + timedelta(days=3) if expires_at is None
        else expires_at,
        status=status,
    )
    db.session.add(r)
    db.session.commit()
    return r


def _other_member(db, name):
    u = User(username=name, email=f'{name}@example.com')
    u.set_password('pw123456')
    db.session.add(u)
    db.session.commit()
    return u


# ---- Model-level ordering -----------------------------------------------------

def test_sole_reservation_is_position_one(db, member, book):
    now = datetime.utcnow()
    r = _reservation(db, member, book, now)
    assert r.queue_position == 1
    assert r.queue_length == 1
    assert r.queue_label == "You're next in line"


def test_positions_follow_reservation_order(db, member, book):
    now = datetime.utcnow()
    second_member = _other_member(db, 'second')
    third_member = _other_member(db, 'third')

    first = _reservation(db, member, book, now)
    second = _reservation(db, second_member, book, now + timedelta(minutes=5))
    third = _reservation(db, third_member, book, now + timedelta(minutes=10))

    assert first.queue_position == 1
    assert second.queue_position == 2
    assert third.queue_position == 3
    assert first.queue_length == second.queue_length == third.queue_length == 3

    assert first.queue_label == "You're next in line"
    assert second.queue_label == '#2 in line'
    assert third.queue_label == '#3 in line'


def test_cancelled_reservations_do_not_occupy_a_queue_slot(db, member, book):
    now = datetime.utcnow()
    second_member = _other_member(db, 'second')

    first = _reservation(db, member, book, now, status='cancelled')
    second = _reservation(db, second_member, book, now + timedelta(minutes=5))

    # The cancelled reservation is first by date but isn't active, so it
    # must not count as "ahead" of the still-active one.
    assert second.queue_position == 1
    assert second.queue_length == 1
    assert first.queue_position is None  # not applicable -- not active


def test_queue_position_ties_broken_by_id_consistently_with_fulfilment(db, member, book):
    """If two reservations somehow share a timestamp, queue_position must
    agree with which one get_active_reservation() would actually fulfil
    first -- otherwise "#1" would lie about who is served next."""
    same_instant = datetime.utcnow()
    second_member = _other_member(db, 'second')

    first = _reservation(db, member, book, same_instant)
    second = _reservation(db, second_member, book, same_instant)

    assert first.id < second.id
    assert first.queue_position == 1
    assert second.queue_position == 2
    assert Reservation.get_active_reservation(book.id).id == first.id


# ---- Rendered page -------------------------------------------------------------

def test_reservations_page_shows_position_for_sole_reservation(client, db, member, book):
    _reservation(db, member, book, datetime.utcnow())
    login(client, 'member', 'memberpass')
    resp = client.get('/reservations')
    assert resp.status_code == 200
    assert b'next in line' in resp.data.lower()
    # Only one person waiting -- the "N members waiting" note is redundant
    # here and must not appear.
    assert b'members waiting' not in resp.data


def test_reservations_page_shows_position_when_others_are_waiting(client, db, member, book):
    now = datetime.utcnow()
    first_member = _other_member(db, 'ahead')
    _reservation(db, first_member, book, now)
    mine = _reservation(db, member, book, now + timedelta(minutes=1))

    login(client, 'member', 'memberpass')
    resp = client.get('/reservations')
    assert resp.status_code == 200
    assert f'#{mine.queue_position}'.encode() in resp.data
    assert b'2 members waiting' in resp.data


# ---- Expiry countdown ---------------------------------------------------------
#
# days_until_expiry and expiry_label drive real UI -- the `is-soon` state and
# two branches in member/reservations.html, and the label rendered twice in
# member/search.html -- but had no coverage until now. Every case below pins
# the clock, both so the assertions are deterministic and so the fixtures
# stay honest examples for anyone adding to this file later.

@pytest.mark.parametrize('offset, expected_days, expected_label', [
    (timedelta(days=3), 3, '3 days left'),
    (timedelta(days=2), 2, '2 days left'),
    (timedelta(days=1), 1, '1 day left'),      # singular, not "1 days left"
    (timedelta(days=0), 0, 'Expires today'),
    (timedelta(days=-1), -1, 'Expired'),
    (timedelta(days=-9), -9, 'Expired'),       # no day count once expired
])
def test_expiry_countdown_and_label(db, member, book, pinned_clock,
                                    offset, expected_days, expected_label):
    r = _reservation(db, member, book, pinned_clock,
                     expires_at=pinned_clock + offset)

    assert r.days_until_expiry == expected_days
    assert r.expiry_label == expected_label


def test_expiry_is_judged_in_local_days_not_utc_ones(db, member, book, pinned_clock):
    """A reservation expiring early today is 'Expires today', even though the
    stored UTC timestamp falls on the previous calendar day.

    The library runs at UTC+8, so 07:00 local is 23:00 UTC *yesterday*. Judging
    this on the stored UTC date would report it already expired, hours before
    it actually is -- the same divergence days_until_due exists to get right
    (see models.Reservation.days_until_expiry, which documents the match).
    """
    expires_local_0700 = pinned_clock - timedelta(hours=2)
    assert expires_local_0700.date() < to_local(pinned_clock).date()   # UTC says yesterday

    r = _reservation(db, member, book, pinned_clock, expires_at=expires_local_0700)

    assert r.days_until_expiry == 0
    assert r.expiry_label == 'Expires today'


def test_expiry_label_is_blank_without_an_expiration_date(pinned_clock):
    """Both properties guard a missing date, and reservations.html branches on
    `is not none` -- so the guard is reachable from a template even though the
    column itself is NOT NULL. Built unsaved, since the database won't hold it.
    """
    r = Reservation(expiration_date=None)

    assert r.days_until_expiry is None
    assert r.expiry_label == ''
