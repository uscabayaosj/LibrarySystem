"""Web Push delivery: mirror in-app notices to subscribed devices.

The notice record (models.Notification) is the source of truth; this is a
best-effort echo of it to the member's phone, plus the number the installed
app should show on its icon. Every failure is logged and swallowed -- a push
that does not arrive must never break the desk action that raised it.

Off unless VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY are set. `python -m push
--generate` prints a fresh pair.
"""
import json
import logging
import sys
from datetime import datetime

import sqlalchemy as sa
from flask import current_app, url_for

log = logging.getLogger(__name__)

# Endpoints the push service says are gone for good. Anything else (5xx,
# a network blip) is transient: keep the subscription and try next time.
_GONE = {404, 410}


def enabled():
    cfg = current_app.config
    return bool(cfg.get('VAPID_PUBLIC_KEY') and cfg.get('VAPID_PRIVATE_KEY'))


def deliver(notices):
    """Send one push per (user_id, title, body, link_endpoint) tuple.

    Runs in the session's after_commit hook, where the ORM session may not
    emit SQL, so everything here goes through a Core connection of its own.
    """
    if not notices or not enabled():
        return 0
    from extensions import db
    from models import PushSubscription, Notification

    sent = 0
    with db.engine.connect() as conn:
        subs = PushSubscription.__table__
        notes = Notification.__table__
        for user_id, title, body, link_endpoint in notices:
            unread = conn.execute(
                sa.select(sa.func.count(notes.c.id)).where(
                    notes.c.user_id == user_id, notes.c.read_at.is_(None))
            ).scalar_one()
            rows = conn.execute(
                sa.select(subs.c.id, subs.c.endpoint, subs.c.p256dh, subs.c.auth)
                .where(subs.c.user_id == user_id)
            ).all()
            if not rows:
                continue
            payload = json.dumps({
                'title': title,
                'body': body or '',
                'url': url_for(link_endpoint) if link_endpoint else url_for('member.notifications'),
                'badge': unread,
            })
            for row in rows:
                status = _send(row.endpoint, row.p256dh, row.auth, payload)
                if status in _GONE:
                    conn.execute(sa.delete(subs).where(subs.c.id == row.id))
                elif status is not None and status < 300:
                    conn.execute(sa.update(subs).where(subs.c.id == row.id)
                                 .values(last_seen_at=datetime.utcnow()))
                    sent += 1
        conn.commit()
    return sent


def _send(endpoint, p256dh, auth, payload):
    """Push one payload to one device. Returns the HTTP status the push
    service answered with, or None when the request never completed."""
    from pywebpush import webpush, WebPushException
    cfg = current_app.config
    try:
        resp = webpush(
            subscription_info={'endpoint': endpoint,
                               'keys': {'p256dh': p256dh, 'auth': auth}},
            data=payload,
            vapid_private_key=cfg['VAPID_PRIVATE_KEY'],
            vapid_claims={'sub': cfg['VAPID_SUBJECT']},
            ttl=60 * 60 * 24,
            timeout=10,
        )
        return resp.status_code
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status not in _GONE:
            log.warning('push to %s failed: %s', endpoint[:60], exc)
        return status
    except Exception as exc:  # network, DNS, TLS -- never the desk's problem
        log.warning('push to %s errored: %s', endpoint[:60], exc)
        return None


def generate_keys():
    """A fresh VAPID pair as the two base64url strings the config expects."""
    import base64
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid
    v = Vapid()
    v.generate_keys()
    raw_private = v.private_key.private_numbers().private_value.to_bytes(32, 'big')
    raw_public = v.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=').decode()
    return b64(raw_public), b64(raw_private)


if __name__ == '__main__':
    if '--generate' in sys.argv:
        public, private = generate_keys()
        print(f'VAPID_PUBLIC_KEY={public}')
        print(f'VAPID_PRIVATE_KEY={private}')
    else:
        print('usage: python -m push --generate')
