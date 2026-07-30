"""Tests for the reservation queue-position indicator."""
from datetime import datetime, timedelta

from models import Reservation, User
from tests.conftest import login


def _reservation(db, user, book, reserved_at, status='active'):
    r = Reservation(
        user_id=user.id, book_id=book.id,
        reservation_date=reserved_at,
        expiration_date=reserved_at + timedelta(days=3),
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
