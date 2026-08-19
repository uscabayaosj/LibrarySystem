"""Tests for the organization branding feature: settings model, theming
derivation, logo validation/rendering, and the admin settings + branding
routes.

The logo lives as bytes on OrganizationSettings, not as a file on disk (see
branding_images.py's module docstring for why), so unlike the file-based
version of this feature there is no "database and disk drifted apart" class
of bug to test for -- the row is the only place the logo exists."""
import io

from PIL import Image

from models import OrganizationSettings
from theming import (
    normalize_hex, build_theme, build_theme_css, contrast_ratio, hex_to_rgb,
    WHITE, DARK_BG_CONTENT,
)
from branding_images import (
    validate_and_reencode, render_icon, render_favicon, ICON_SPECS,
    LogoValidationError, MAX_UPLOAD_BYTES,
)
from tests.conftest import login


def _png_bytes(size=(600, 600), color=(41, 33, 104, 255)):
    buf = io.BytesIO()
    Image.new('RGBA', size, color).save(buf, format='PNG')
    buf.seek(0)
    return buf


class _FakeFileStorage:
    """Minimal stand-in for werkzeug's FileStorage, exposing just the
    .stream attribute validate_and_reencode relies on."""

    def __init__(self, stream, filename='logo.png'):
        self.stream = stream
        self.filename = filename


def _upload_logo(client):
    return client.post('/admin/settings', data={
        'org_name': 'Test Org', 'theme_color': '',
        'logo': (_png_bytes(), 'mylogo.png'),
    }, content_type='multipart/form-data', follow_redirects=True)


# ---- OrganizationSettings model ----------------------------------------------

def test_get_creates_singleton_with_defaults(app, db):
    settings = OrganizationSettings.get()
    assert settings.id == 1
    assert settings.org_name == 'Library System'
    assert settings.logo_data is None
    assert settings.theme_color is None


def test_get_returns_same_row_on_repeat_calls(app, db):
    first = OrganizationSettings.get()
    first.org_name = 'Test University Library'
    db.session.commit()
    second = OrganizationSettings.get()
    assert second.org_name == 'Test University Library'


def test_logo_ready_false_with_no_upload(app, db):
    assert OrganizationSettings.get().logo_ready is False


def test_logo_ready_true_once_bytes_are_set(app, db):
    settings = OrganizationSettings.get()
    settings.logo_data = b'not real image bytes, just needs to be non-null'
    db.session.commit()
    assert settings.logo_ready is True


def test_icon_url_falls_back_to_bundled_default_without_a_logo(app, db):
    with app.test_request_context():
        settings = OrganizationSettings.get()
        assert settings.logo_url is None
        assert '/static/icons/icon-192.png' in settings.icon_url('icon-192')
        assert '/static/icons/favicon.ico' in settings.favicon_url


def test_icon_url_points_at_the_branding_route_with_a_logo(app, db):
    with app.test_request_context():
        settings = OrganizationSettings.get()
        settings.logo_data = b'x'
        from datetime import datetime
        settings.logo_updated_at = datetime(2026, 1, 1)
        assert '/branding/logo' in settings.logo_url
        assert '/branding/icon/icon-192.png' in settings.icon_url('icon-192')
        assert '/branding/favicon.ico' in settings.favicon_url
        # Cache-busted by the upload time, not left to the browser's guess.
        assert 'v=' in settings.logo_url


# ---- theming.py ----------------------------------------------------------------

def test_normalize_hex_accepts_valid_and_rejects_invalid():
    assert normalize_hex('#292168') == '#292168'
    assert normalize_hex('292168') == '#292168'
    assert normalize_hex('#fff') is None  # 3-digit shorthand rejected
    assert normalize_hex('not-a-color') is None
    assert normalize_hex('') is None
    assert normalize_hex(None) is None


def test_build_theme_is_none_for_invalid_color():
    assert build_theme('nonsense') is None


def test_build_theme_derives_wcag_aa_safe_tokens():
    theme = build_theme('#FF00FF')  # highly saturated, unlikely to already be AA-safe
    fill_rgb = hex_to_rgb(theme['light']['accent_fill'])
    assert contrast_ratio(fill_rgb, WHITE) >= 4.5

    dark_rgb = hex_to_rgb(theme['dark']['accent'])
    assert contrast_ratio(dark_rgb, DARK_BG_CONTENT) >= 4.5


def test_build_theme_css_contains_expected_selectors():
    css = build_theme_css('#292168')
    assert ':root, :root[data-appearance="light"]' in css
    assert '@media (prefers-color-scheme: dark)' in css
    assert ':root[data-appearance="dark"]' in css
    assert '--accent-fill:' in css


def test_build_theme_css_empty_for_invalid_color():
    assert build_theme_css('garbage') == ''


# ---- branding_images.py: validation ---------------------------------------------

def test_validate_and_reencode_accepts_a_valid_png():
    data, content_type = validate_and_reencode(_FakeFileStorage(_png_bytes()))
    assert content_type == 'image/png'
    # Re-encoded, decodable bytes -- not just a pass-through of the input.
    Image.open(io.BytesIO(data)).verify()


def test_validate_and_reencode_rejects_non_image_file():
    fs = _FakeFileStorage(io.BytesIO(b'this is definitely not an image'))
    try:
        validate_and_reencode(fs)
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'not a valid image' in str(e)


def test_validate_and_reencode_rejects_oversized_file():
    buf = io.BytesIO(b'\x00' * (MAX_UPLOAD_BYTES + 1))
    try:
        validate_and_reencode(_FakeFileStorage(buf))
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'too large' in str(e)


def test_validate_and_reencode_rejects_empty_file():
    try:
        validate_and_reencode(_FakeFileStorage(io.BytesIO(b'')))
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'No file' in str(e)


def test_validate_and_reencode_rejects_oversized_dimensions():
    fs = _FakeFileStorage(_png_bytes(size=(3000, 3000)))
    try:
        validate_and_reencode(fs)
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'too large' in str(e)


def test_validate_and_reencode_handles_jpeg_and_flattens_to_rgb():
    buf = io.BytesIO()
    Image.new('RGB', (600, 600), (10, 20, 30)).save(buf, format='JPEG')
    buf.seek(0)
    data, content_type = validate_and_reencode(_FakeFileStorage(buf, filename='logo.jpg'))
    assert content_type == 'image/jpeg'
    assert Image.open(io.BytesIO(data)).mode == 'RGB'


# ---- branding_images.py: derived-icon rendering ----------------------------------

def test_render_icon_produces_every_declared_variant_at_its_own_size():
    logo_bytes, _ = validate_and_reencode(_FakeFileStorage(_png_bytes()))
    for variant, (canvas_size, _ratio, _mode) in ICON_SPECS.items():
        png_bytes = render_icon(logo_bytes, variant)
        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (canvas_size, canvas_size), variant


def test_render_icon_flattens_apple_touch_icon_to_rgb_only():
    logo_bytes, _ = validate_and_reencode(_FakeFileStorage(_png_bytes()))
    img = Image.open(io.BytesIO(render_icon(logo_bytes, 'apple-touch-icon')))
    assert img.mode == 'RGB'


def test_render_favicon_produces_a_multi_frame_ico():
    logo_bytes, _ = validate_and_reencode(_FakeFileStorage(_png_bytes()))
    ico_bytes = render_favicon(logo_bytes)
    img = Image.open(io.BytesIO(ico_bytes))
    assert img.format == 'ICO'


# ---- /admin/settings route -------------------------------------------------------

def test_settings_route_requires_admin(client, db, member):
    login(client, 'member', 'memberpass')
    resp = client.get('/admin/settings', follow_redirects=True)
    assert resp.status_code == 200
    assert b'do not have permission' in resp.data


def test_settings_route_updates_org_name_and_theme_color(client, db, admin):
    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/settings', data={
        'org_name': 'Ateneo de Davao University Library',
        'theme_color': '#228B22',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Branding updated' in resp.data

    settings = OrganizationSettings.get()
    assert settings.org_name == 'Ateneo de Davao University Library'
    assert settings.theme_color == '#228b22'


def test_settings_route_rejects_invalid_theme_color(client, db, admin):
    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/settings', data={
        'org_name': 'Test Org', 'theme_color': 'not-a-hex',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'valid hex color' in resp.data
    settings = OrganizationSettings.get()
    assert settings.theme_color is None  # unchanged


def test_settings_route_rejects_blank_org_name(client, db, admin):
    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/settings', data={'org_name': '', 'theme_color': ''},
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b'required' in resp.data


def test_settings_route_uploads_logo(client, db, admin):
    login(client, 'admin', 'adminpass')
    resp = _upload_logo(client)
    assert resp.status_code == 200
    assert b'Branding updated' in resp.data

    settings = OrganizationSettings.get()
    assert settings.logo_ready is True
    assert settings.logo_content_type == 'image/png'
    assert settings.logo_updated_at is not None


def test_settings_route_upload_is_immediately_servable(client, db, admin):
    login(client, 'admin', 'adminpass')
    _upload_logo(client)

    resp = client.get('/branding/logo')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'image/png'
    Image.open(io.BytesIO(resp.data)).verify()


def test_settings_route_removal_clears_the_row(client, db, admin):
    login(client, 'admin', 'adminpass')
    _upload_logo(client)
    assert OrganizationSettings.get().logo_ready is True

    resp = client.post('/admin/settings', data={
        'org_name': 'Test Org', 'theme_color': '', 'remove_logo': 'on',
    }, content_type='multipart/form-data', follow_redirects=True)

    assert resp.status_code == 200
    settings = OrganizationSettings.get()
    assert settings.logo_data is None
    assert settings.logo_content_type is None
    assert settings.logo_updated_at is None
    # And the previously-servable URL is gone with it -- nothing left
    # publicly reachable after removal.
    assert client.get('/branding/logo').status_code == 404


def test_manifest_route_reflects_org_name(client, db):
    settings = OrganizationSettings.get()
    settings.org_name = 'My Custom Org'
    db.session.commit()

    resp = client.get('/manifest.json')
    assert resp.status_code == 200
    assert resp.json['name'] == 'My Custom Org'
    assert resp.json['short_name'] == 'My Custom Org'[:12]


def test_manifest_uses_bundled_icons_without_a_logo(client, db):
    icons = client.get('/manifest.json').json['icons']
    srcs = [i['src'] for i in icons]
    assert all('/static/icons/' in s for s in srcs), srcs


def test_manifest_uses_branding_route_icons_once_a_logo_is_uploaded(client, db, admin):
    login(client, 'admin', 'adminpass')
    _upload_logo(client)

    icons = client.get('/manifest.json').json['icons']
    srcs = [i['src'] for i in icons]
    assert all('/branding/icon/' in s for s in srcs), srcs


def test_pages_fall_back_to_default_mark_without_a_logo(client, db):
    body = client.get('/login').get_data(as_text=True)
    assert '/branding/logo' not in body


# ---- /branding routes ------------------------------------------------------------

def test_branding_logo_404s_without_an_upload(client, db):
    assert client.get('/branding/logo').status_code == 404


def test_branding_icon_renders_every_declared_variant(client, db, admin):
    login(client, 'admin', 'adminpass')
    _upload_logo(client)
    for variant, (canvas_size, _ratio, _mode) in ICON_SPECS.items():
        resp = client.get('/branding/icon/%s.png' % variant)
        assert resp.status_code == 200, variant
        assert resp.headers['Content-Type'] == 'image/png'
        img = Image.open(io.BytesIO(resp.data))
        assert img.size == (canvas_size, canvas_size), variant


def test_branding_icon_404s_for_an_unknown_variant(client, db, admin):
    login(client, 'admin', 'adminpass')
    _upload_logo(client)
    assert client.get('/branding/icon/not-a-real-variant.png').status_code == 404


def test_branding_favicon_renders(client, db, admin):
    login(client, 'admin', 'adminpass')
    _upload_logo(client)
    resp = client.get('/branding/favicon.ico')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'image/vnd.microsoft.icon'


def test_branding_logo_response_is_cached_hard(client, db, admin):
    login(client, 'admin', 'adminpass')
    _upload_logo(client)
    resp = client.get('/branding/logo')
    assert 'max-age=31536000' in resp.headers['Cache-Control']
    assert 'immutable' in resp.headers['Cache-Control']
