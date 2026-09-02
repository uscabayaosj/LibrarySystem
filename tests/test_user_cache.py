"""Flask-Login reloads the signed-in user on every request. On a serverless
host that is a full trip to the database before any page can start, so the
row is cached in the process for a short while. These pin the two things
that matter: a hit costs nothing, and a write to the row is never hidden."""
from models import User


def _load(app, user_id):
    return app.login_manager._user_callback(str(user_id))


def test_repeat_user_loads_cost_no_query(app, db, member, count_queries):
    _load(app, member.id)
    db.session.remove()
    count_queries.n = 0
    user = _load(app, member.id)
    assert count_queries.n == 0
    assert user.username == 'member'
    assert user.check_password('memberpass')


def test_cached_user_is_a_live_row_with_fresh_per_request_state(app, db, member):
    _load(app, member.id)
    db.session.remove()
    user = _load(app, member.id)
    # Session-attached: routes edit current_user and commit.
    user.phone = '0917'
    db.session.commit()
    assert User.query.get(member.id).phone == '0917'


def test_password_change_is_visible_on_the_next_load(app, db, member):
    _load(app, member.id)
    db.session.remove()
    user = _load(app, member.id)
    user.set_password('newpass')
    db.session.commit()
    db.session.remove()
    assert _load(app, member.id).check_password('newpass')


def test_deleted_user_no_longer_loads(app, db, member):
    _load(app, member.id)
    uid = member.id
    db.session.delete(member)
    db.session.commit()
    db.session.remove()
    assert _load(app, uid) is None


def test_unknown_user_loads_as_none_without_poisoning_the_cache(app, db, count_queries):
    assert _load(app, 999999) is None
    count_queries.n = 0
    assert _load(app, 999999) is None
    assert count_queries.n == 1
