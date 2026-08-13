"""The library's local timezone, for user-facing date math.

Every timestamp is stored in the database as a naive UTC instant (the
standard practice) and datetime.utcnow() still governs anything that's
really about the exact moment -- ordering, "is this loan currently overdue"
comparisons, session timestamps. Those stay untouched.

But "which calendar day is this?" -- due today vs. tomorrow, a due date
formatted for display, a reminder's calendar-app entry -- has to be judged
in the library's own timezone, not the server's UTC clock, or the day
boundary can be wrong by the offset for a chunk of every day. This project's
target deployment is a Philippine school library (see PRODUCT.md); the
Philippines does not observe daylight saving time, so a fixed UTC+8 offset
is exact year-round and needs no zoneinfo/tzdata dependency.
"""
from datetime import datetime, timedelta, timezone

LIBRARY_TZ = timezone(timedelta(hours=8), name='Asia/Manila')


def local_now():
    """The current moment, expressed in the library's local timezone."""
    return datetime.now(LIBRARY_TZ)


def to_local(naive_utc_dt):
    """Convert a naive-UTC datetime (as stored in the database) to the
    library's local timezone. Returns None if given None, so call sites can
    chain straight onto an optional field without a separate guard."""
    if naive_utc_dt is None:
        return None
    return naive_utc_dt.replace(tzinfo=timezone.utc).astimezone(LIBRARY_TZ)
