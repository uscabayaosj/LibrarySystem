"""Tests for the .ics due-date/expiry calendar export."""
from datetime import datetime, timedelta

from models import Reservation
from calendar_export import build_ics
from tests.conftest import login


# ---- build_ics() ------------------------------------------------------------

def test_build_ics_contains_required_vevent_fields():
    ics = build_ics(
        uid='loan-1@library-system',
        summary='Return "Test Book"',
        description='"Test Book" is due back.',
        event_date=datetime(2026, 8, 15),
        reminder_days_before=1,
        alarm_description='"Test Book" is due tomorrow',
    )
    assert ics.startswith('BEGIN:VCALENDAR\r\n')
    assert ics.endswith('END:VCALENDAR\r\n')
    assert 'UID:loan-1@library-system' in ics
    assert 'DTSTART;VALUE=DATE:20260815' in ics
    assert 'DTEND;VALUE=DATE:20260816' in ics
    assert 'SUMMARY:Return "Test Book"' in ics
    assert 'BEGIN:VALARM' in ics
    assert 'TRIGGER:-P1D' in ics
    assert 'END:VALARM' in ics
    # Lines are CRLF-terminated per RFC 5545, not bare \n.
    assert '\r\n' in ics
    assert '\n\n' not in ics.replace('\r\n', '')


def test_build_ics_escapes_special_characters():
    ics = build_ics(
        uid='x@y', summary='Comma, semicolon; backslash\\',
        description='Line one\nLine two', event_date=datetime(2026, 1, 1),
    )
    assert 'SUMMARY:Comma\\, semicolon\\; backslash\\\\' in ics
    assert 'DESCRIPTION:Line one\\nLine two' in ics


def test_build_ics_folds_long_lines():
    ics = build_ics(
        uid='x@y', summary='A' * 200,
        description='short', event_date=datetime(2026, 1, 1),
    )
    for line in ics.split('\r\n'):
        assert len(line) <= 75


def test_build_ics_accepts_date_or_datetime():
    from datetime import date
    ics_date = build_ics(uid='a', summary='s', description='d', event_date=date(2026, 3, 1))
    ics_datetime = build_ics(uid='a', summary='s', description='d',
                              event_date=datetime(2026, 3, 1, 23, 59))
    assert 'DTSTART;VALUE=DATE:20260301' in ics_date
    assert 'DTSTART;VALUE=DATE:20260301' in ics_datetime


# ---- /loans/<id>/calendar.ics route -----------------------------------------

def _active_loan(db, user, book, due_in_days=5):
    from models import Borrowing
    b = Borrowing(
        user_id=user.id, book_id=book.id,
        due_date=datetime.utcnow() + timedelta(days=due_in_days),
        status='active',
    )
    db.session.add(b)
    db.session.commit()
    return b


def test_loan_calendar_route_returns_ics(client, db, member, book):
    login(client, 'member', 'memberpass')
    loan = _active_loan(db, member, book)

    resp = client.get(f'/loans/{loan.id}/calendar.ics')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/calendar'
    assert 'attachment' in resp.headers['Content-Disposition']
    assert b'BEGIN:VCALENDAR' in resp.data
    assert book.title.encode() in resp.data


def test_loan_calendar_route_rejects_other_members_loan(client, db, member, book):
    from models import User
    other = User(username='other', email='other@example.com')
    other.set_password('otherpass123')
    db.session.add(other)
    db.session.commit()
    loan = _active_loan(db, other, book)

    login(client, 'member', 'memberpass')
    resp = client.get(f'/loans/{loan.id}/calendar.ics')
    assert resp.status_code == 403


def test_loan_calendar_route_redirects_when_already_returned(client, db, member, book):
    loan = _active_loan(db, member, book)
    loan.status = 'returned'
    loan.return_date = datetime.utcnow()
    db.session.commit()

    login(client, 'member', 'memberpass')
    resp = client.get(f'/loans/{loan.id}/calendar.ics', follow_redirects=True)
    assert resp.status_code == 200
    assert b'already been returned' in resp.data


def test_loan_calendar_route_requires_login(client, db, member, book):
    loan = _active_loan(db, member, book)
    resp = client.get(f'/loans/{loan.id}/calendar.ics')
    assert resp.status_code in (302, 401)


# ---- /reservations/<id>/calendar.ics route -----------------------------------

def _active_reservation(db, user, book, expires_in_days=3):
    r = Reservation(
        user_id=user.id, book_id=book.id,
        expiration_date=datetime.utcnow() + timedelta(days=expires_in_days),
        status='active',
    )
    db.session.add(r)
    db.session.commit()
    return r


def test_reservation_calendar_route_returns_ics(client, db, member, book):
    login(client, 'member', 'memberpass')
    reservation = _active_reservation(db, member, book)

    resp = client.get(f'/reservations/{reservation.id}/calendar.ics')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/calendar'
    assert b'BEGIN:VCALENDAR' in resp.data
    assert book.title.encode() in resp.data


def test_reservation_calendar_route_rejects_other_members_reservation(client, db, member, book):
    from models import User
    other = User(username='other2', email='other2@example.com')
    other.set_password('otherpass123')
    db.session.add(other)
    db.session.commit()
    reservation = _active_reservation(db, other, book)

    login(client, 'member', 'memberpass')
    resp = client.get(f'/reservations/{reservation.id}/calendar.ics')
    assert resp.status_code == 403


def test_reservation_calendar_route_redirects_when_not_active(client, db, member, book):
    reservation = _active_reservation(db, member, book)
    reservation.status = 'cancelled'
    db.session.commit()

    login(client, 'member', 'memberpass')
    resp = client.get(f'/reservations/{reservation.id}/calendar.ics', follow_redirects=True)
    assert resp.status_code == 200
    assert b'no longer active' in resp.data
