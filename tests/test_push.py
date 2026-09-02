"""Web Push: subscriptions, delivery after commit, the icon badge count,
and the versioned service worker that carries the update prompt."""
from datetime import datetime, timedelta

import pytest

import push
from models import Notification, PushSubscription, Borrowing
from tests.conftest import login


SUB = {'endpoint': 'https://push.example/abc',
       'keys': {'p256dh': 'p256', 'auth': 'auth'}}


@pytest.fixture
def push_enabled(app):
    app.config['VAPID_PUBLIC_KEY'] = 'pub'
    app.config['VAPID_PRIVATE_KEY'] = 'priv'
    yield
    app.config['VAPID_PUBLIC_KEY'] = ''
    app.config['VAPID_PRIVATE_KEY'] = ''


@pytest.fixture
def sent(monkeypatch):
    """Capture every push the app tries to send instead of hitting a push
    service. Each entry is (endpoint, payload dict)."""
    import json
    calls = []
    statuses = {}

    def fake_send(endpoint, p256dh, auth, payload):
        calls.append((endpoint, json.loads(payload)))
        return statuses.get(endpoint, 201)

    monkeypatch.setattr(push, '_send', fake_send)
    calls_obj = type('Sent', (), {})()
    calls_obj.calls = calls
    calls_obj.statuses = statuses
    return calls_obj


def test_member_can_subscribe_and_unsubscribe(client, db, member):
    login(client, 'member', 'memberpass')
    assert client.post('/push/subscribe', json=SUB).status_code == 204
    row = PushSubscription.query.one()
    assert row.user_id == member.id and row.endpoint == SUB['endpoint']

    assert client.post('/push/unsubscribe', json={'endpoint': SUB['endpoint']}).status_code == 204
    assert PushSubscription.query.count() == 0


def test_resubscribing_the_same_device_rebinds_it_to_the_current_member(client, db, member):
    from models import User
    other = User(username='other', email='o@example.com'); other.set_password('pw')
    db.session.add(other); db.session.commit()

    login(client, 'member', 'memberpass')
    client.post('/push/subscribe', json=SUB)
    client.get('/logout')
    login(client, 'other', 'pw')
    client.post('/push/subscribe', json=SUB)

    rows = PushSubscription.query.all()
    assert len(rows) == 1 and rows[0].user_id == other.id


def test_subscribe_rejects_junk_and_admins(client, db, member, admin):
    login(client, 'member', 'memberpass')
    assert client.post('/push/subscribe', json={'endpoint': 'http://insecure'}).status_code == 400
    assert client.post('/push/subscribe', json={'endpoint': 'https://x', 'keys': {}}).status_code == 400
    client.get('/logout')
    login(client, 'admin', 'adminpass')
    assert client.post('/push/subscribe', json=SUB).status_code == 403


def test_badge_count_is_the_unread_notice_count(client, db, member):
    login(client, 'member', 'memberpass')
    Notification.push(member.id, 'due_soon', 'A'); Notification.push(member.id, 'overdue', 'B')
    db.session.commit()
    # The suite runs every client request inside one app context, so
    # Flask-Login hands back the same user object each time; reset its
    # per-request memo the way a real request boundary would.
    member._invalidate_borrow_state()
    assert client.get('/badge-count').get_json() == {'count': 2}
    client.post('/notifications/read')
    member._invalidate_borrow_state()
    assert client.get('/badge-count').get_json() == {'count': 0}


def test_a_committed_notice_is_pushed_with_the_unread_badge(app, db, member, push_enabled, sent):
    with app.test_request_context():
        db.session.add(PushSubscription(user_id=member.id, endpoint=SUB['endpoint'],
                                        p256dh='p', auth='a'))
        db.session.commit()
        Notification.push(member.id, 'hold_ready', '"Dune" is ready to collect',
                          'Collect it from the desk.', 'member.reservations')
        db.session.commit()

    assert len(sent.calls) == 1
    endpoint, payload = sent.calls[0]
    assert endpoint == SUB['endpoint']
    assert payload['title'] == '"Dune" is ready to collect'
    assert payload['url'] == '/reservations'
    assert payload['badge'] == 1


def test_nothing_is_pushed_without_keys(app, db, member, sent):
    with app.test_request_context():
        db.session.add(PushSubscription(user_id=member.id, endpoint=SUB['endpoint'],
                                        p256dh='p', auth='a'))
        Notification.push(member.id, 'overdue', 'Late')
        db.session.commit()
    assert sent.calls == []


def test_a_gone_endpoint_is_forgotten(app, db, member, push_enabled, sent):
    sent.statuses[SUB['endpoint']] = 410
    with app.test_request_context():
        db.session.add(PushSubscription(user_id=member.id, endpoint=SUB['endpoint'],
                                        p256dh='p', auth='a'))
        Notification.push(member.id, 'overdue', 'Late')
        db.session.commit()
    assert PushSubscription.query.count() == 0


def test_the_sweep_pushes_each_new_notice_once(app, db, member, book, push_enabled, sent, monkeypatch):
    with app.test_request_context():
        db.session.add(PushSubscription(user_id=member.id, endpoint=SUB['endpoint'],
                                        p256dh='p', auth='a'))
        db.session.add(Borrowing(user_id=member.id, book_id=book.id,
                                 due_date=datetime.utcnow() - timedelta(days=3), status='active'))
        db.session.commit()
        Notification.sweep_loans(); db.session.commit()
        Notification.sweep_loans(); db.session.commit()   # idempotent: no second push
    assert len(sent.calls) == 1
    assert 'overdue' in sent.calls[0][1]['title']


def test_service_worker_is_versioned_and_uncached(client, db):
    res = client.get('/sw.js')
    assert res.status_code == 200
    assert res.mimetype == 'application/javascript'
    assert res.headers['Cache-Control'] == 'no-cache'
    body = res.get_data(as_text=True)
    assert "var VERSION = '" in body and "VERSION = ''" not in body
    assert "addEventListener('push'" in body


def test_generated_vapid_keys_are_a_usable_pair():
    public, private = push.generate_keys()
    assert len(public) == 87 and len(private) == 43      # 65- and 32-byte keys, base64url, no padding
    from pywebpush import Vapid
    assert Vapid.from_string(private) is not None
