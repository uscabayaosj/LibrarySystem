"""Minimal iCalendar (RFC 5545) event generation.

No dependency is added for this -- a due-date/expiry reminder is one VEVENT
with a single VALARM, which is a small, stable, hand-writable format. This
covers exactly the "reminders" a phone borrower needs: opening the .ics adds
a calendar event with a built-in alarm, using each phone's own native
Calendar app rather than a push-notification server this project doesn't
otherwise have any infrastructure for.
"""
from datetime import date, timedelta


def _escape(text):
    """Escape TEXT-value special characters per RFC 5545 §3.3.11."""
    return (
        text.replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _fold(line):
    """Fold lines longer than 75 octets onto a continuation line, per
    RFC 5545 §3.1. Most calendar apps tolerate long lines, but folding keeps
    this a well-formed .ics regardless of what opens it."""
    if len(line) <= 75:
        return line
    out = [line[:75]]
    rest = line[75:]
    while rest:
        out.append(' ' + rest[:74])
        rest = rest[74:]
    return '\r\n'.join(out)


def build_ics(uid, summary, description, event_date, reminder_days_before=1,
              alarm_description=None):
    """Build a one-day all-day VEVENT calendar (a due date is a day, not a
    moment) with a VALARM firing `reminder_days_before` days ahead.

    uid: a stable, globally-unique identifier for this event (so re-adding
         the same loan/reservation updates the existing calendar entry
         rather than duplicating it).
    event_date: a date (or datetime -- only the date part is used).
    """
    if hasattr(event_date, 'date'):
        event_date = event_date.date()
    dtstart = event_date.strftime('%Y%m%d')
    dtend = (event_date + timedelta(days=1)).strftime('%Y%m%d')
    dtstamp = date.today().strftime('%Y%m%dT000000Z')

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Library System//Anthropology Department//EN',
        'CALSCALE:GREGORIAN',
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{dtstamp}',
        f'DTSTART;VALUE=DATE:{dtstart}',
        f'DTEND;VALUE=DATE:{dtend}',
        f'SUMMARY:{_escape(summary)}',
        f'DESCRIPTION:{_escape(description)}',
        'BEGIN:VALARM',
        'ACTION:DISPLAY',
        f'DESCRIPTION:{_escape(alarm_description or summary)}',
        f'TRIGGER:-P{reminder_days_before}D',
        'END:VALARM',
        'END:VEVENT',
        'END:VCALENDAR',
    ]
    return '\r\n'.join(_fold(line) for line in lines) + '\r\n'
