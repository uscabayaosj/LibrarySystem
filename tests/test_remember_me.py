"""Tests for the 'Remember me' persistent-login option."""


def _set_cookie_names(resp):
    return [c.split('=')[0] for c in resp.headers.getlist('Set-Cookie')]


def test_login_without_remember_sets_no_remember_cookie(client, member):
    resp = client.post('/login', data={'username': 'member', 'password': 'memberpass'})
    assert resp.status_code == 302
    assert 'remember_token' not in _set_cookie_names(resp)


def test_login_with_remember_sets_remember_cookie(client, member):
    resp = client.post('/login', data={
        'username': 'member', 'password': 'memberpass', 'remember': 'on',
    })
    assert resp.status_code == 302
    assert 'remember_token' in _set_cookie_names(resp)


def test_remember_checkbox_absent_is_treated_as_unchecked(client, member):
    """An unchecked HTML checkbox simply isn't sent in the form data at
    all -- make sure that's handled the same as an explicit 'off'."""
    resp = client.post('/login', data={'username': 'member', 'password': 'memberpass'})
    assert 'remember_token' not in _set_cookie_names(resp)
