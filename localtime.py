"""The library's local timezone, for user-facing date math.

Every timestamp is stored in the database as a naive UTC instant (the
standard practice) and datetime.utcnow() still governs anything that's
really about the exact moment -- ordering, session timestamps. Those stay
untouched.

But "which calendar day is this?" -- due today vs. tomorrow, a due date
formatted for display, a reminder's calendar-app entry -- has to be judged
in the library's own timezone, not the server's UTC clock, or the day
boundary can be wrong by the offset for a chunk of every day.

"Is this loan overdue?" belongs to that second group, not the first. An
earlier version of this docstring listed it as an exact-moment comparison,
and every caller that followed that advice used `due_date < utcnow()` --
which marks a book due *today* as overdue from 08:00 local onward, because
that is when UTC crosses the stored due timestamp. The dashboard then
accused a borrower of being overdue while the badge beside it, derived from
the calendar-date math below, still read "Due today". Use
local_today_start_utc() as the cutoff so a loan turns overdue at local
midnight, in one place, for every caller. This project's
target deployment is a Philippine school library (see PRODUCT.md); the
Philippines does not observe daylight saving time, so a fixed UTC+8 offset
is exact year-round and needs no zoneinfo/tzdata dependency.
"""
from datetime import datetime, timedelta, timezone

LIBRARY_TZ = timezone(timedelta(hours=8), name='Asia/Manila')


def local_now():
    """The current moment, expressed in the library's local timezone."""
    return datetime.now(LIBRARY_TZ)


def local_today_start_utc():
    """Local midnight this morning, as a naive-UTC datetime.

    This is the single overdue cutoff: a loan is overdue exactly when its
    stored due_date is before this instant. It is the SQL-expressible form of
    the `to_local(due_date).date() < local_now().date()` comparison that
    Borrowing.days_until_due does in Python, so a query-side count and a
    property-side badge can never disagree about the same loan -- which they
    did, for the eight hours a day between local and UTC midnight, when each
    call site rolled its own `due_date < utcnow()`.

    Returned naive (tzinfo stripped) because every datetime column in this
    schema is naive-UTC; comparing a naive column against an aware value
    raises in SQLAlchemy on some backends and silently misbehaves on others.
    """
    local_midnight = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def to_local(naive_utc_dt):
    """Convert a naive-UTC datetime (as stored in the database) to the
    library's local timezone. Returns None if given None, so call sites can
    chain straight onto an optional field without a separate guard."""
    if naive_utc_dt is None:
        return None
    return naive_utc_dt.replace(tzinfo=timezone.utc).astimezone(LIBRARY_TZ)
