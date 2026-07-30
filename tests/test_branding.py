"""Tests for the organization branding feature: settings model, theming
derivation, logo upload validation, and the admin settings route."""
import io

from PIL import Image

from models import OrganizationSettings
from theming import (
    normalize_hex, build_theme, build_theme_css, contrast_ratio, hex_to_rgb,
    WHITE, DARK_BG_CONTENT,
)
from logo_upload import validate_and_save, LogoValidationError, MAX_UPLOAD_BYTES
from tests.conftest import login


def _png_bytes(size=(600, 600), color=(0, 105, 217, 255)):
    buf = io.BytesIO()
    Image.new('RGBA', size, color).save(buf, format='PNG')
    buf.seek(0)
    return buf


class _FakeFileStorage:
    """Minimal stand-in for werkzeug's FileStorage, exposing just the
    .stream attribute validate_and_save relies on."""

    def __init__(self, stream, filename='logo.png'):
        self.stream = stream
        self.filename = filename


# ---- OrganizationSettings model ----------------------------------------------

def test_get_creates_singleton_with_defaults(app, db):
    settings = OrganizationSettings.get()
    assert settings.id == 1
    assert settings.org_name == 'Library System'
    assert settings.logo_filename is None
    assert settings.theme_color is None


def test_get_returns_same_row_on_repeat_calls(app, db):
    first = OrganizationSettings.get()
    first.org_name = 'Test University Library'
    db.session.commit()
    second = OrganizationSettings.get()
    assert second.org_name == 'Test University Library'


# ---- theming.py ----------------------------------------------------------------

def test_normalize_hex_accepts_valid_and_rejects_invalid():
    assert normalize_hex('#0069D9') == '#0069d9'
    assert normalize_hex('0069D9') == '#0069d9'
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
    css = build_theme_css('#0069D9')
    assert ':root, :root[data-appearance="light"]' in css
    assert '@media (prefers-color-scheme: dark)' in css
    assert ':root[data-appearance="dark"]' in css
    assert '--accent-fill:' in css


def test_build_theme_css_empty_for_invalid_color():
    assert build_theme_css('garbage') == ''


# ---- logo_upload.py -------------------------------------------------------------

def test_validate_and_save_accepts_a_valid_png(tmp_path):
    fs = _FakeFileStorage(_png_bytes())
    filename = validate_and_save(fs, str(tmp_path))
    assert filename == 'logo.png'
    assert (tmp_path / 'logo.png').exists()
    # Installed-app icon variants are generated alongside it.
    assert (tmp_path / 'icon-192.png').exists()
    assert (tmp_path / 'icon-512.png').exists()
    assert (tmp_path / 'icon-192-maskable.png').exists()
    assert (tmp_path / 'icon-512-maskable.png').exists()
    assert (tmp_path / 'apple-touch-icon.png').exists()
    assert (tmp_path / 'favicon.ico').exists()


def test_validate_and_save_rejects_non_image_file(tmp_path):
    fs = _FakeFileStorage(io.BytesIO(b'this is definitely not an image'))
    try:
        validate_and_save(fs, str(tmp_path))
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'not a valid image' in str(e)


def test_validate_and_save_rejects_oversized_file(tmp_path):
    buf = io.BytesIO(b'\x00' * (MAX_UPLOAD_BYTES + 1))
    fs = _FakeFileStorage(buf)
    try:
        validate_and_save(fs, str(tmp_path))
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'too large' in str(e)


def test_validate_and_save_rejects_empty_file(tmp_path):
    fs = _FakeFileStorage(io.BytesIO(b''))
    try:
        validate_and_save(fs, str(tmp_path))
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'No file' in str(e)


def test_validate_and_save_rejects_oversized_dimensions(tmp_path):
    fs = _FakeFileStorage(_png_bytes(size=(3000, 3000)))
    try:
        validate_and_save(fs, str(tmp_path))
        assert False, 'expected LogoValidationError'
    except LogoValidationError as e:
        assert 'too large' in str(e)


def test_validate_and_save_replaces_previous_logo_of_different_format(tmp_path):
    fs_png = _FakeFileStorage(_png_bytes())
    validate_and_save(fs_png, str(tmp_path))
    assert (tmp_path / 'logo.png').exists()

    buf = io.BytesIO()
    Image.new('RGB', (600, 600), (10, 20, 30)).save(buf, format='JPEG')
    buf.seek(0)
    fs_jpeg = _FakeFileStorage(buf, filename='logo.jpg')
    validate_and_save(fs_jpeg, str(tmp_path))
    assert (tmp_path / 'logo.jpg').exists()
    assert not (tmp_path / 'logo.png').exists()


# ---- /admin/settings route -------------------------------------------------------

def test_settings_route_requires_admin(client, db, member):
    login(client, 'member', 'memberpass')
    resp = client.get('/admin/settings', follow_redirects=True)
    assert resp.status_code == 200
    assert b'do not have permission' in resp.data


def test_settings_route_updates_org_name_and_theme_color(client, db, admin, tmp_path, monkeypatch):
    import routes.admin as admin_routes
    monkeypatch.setattr(admin_routes, '_branding_upload_dir', lambda: str(tmp_path))

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


def test_settings_route_uploads_logo(client, db, admin, tmp_path, monkeypatch):
    import routes.admin as admin_routes
    monkeypatch.setattr(admin_routes, '_branding_upload_dir', lambda: str(tmp_path))

    login(client, 'admin', 'adminpass')
    resp = client.post('/admin/settings', data={
        'org_name': 'Test Org', 'theme_color': '',
        'logo': (_png_bytes(), 'mylogo.png'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Branding updated' in resp.data

    settings = OrganizationSettings.get()
    assert settings.logo_filename == 'logo.png'
    assert (tmp_path / 'logo.png').exists()


def test_manifest_route_reflects_org_name(client, db):
    settings = OrganizationSettings.get()
    settings.org_name = 'My Custom Org'
    db.session.commit()

    resp = client.get('/manifest.json')
    assert resp.status_code == 200
    assert resp.json['name'] == 'My Custom Org'
    assert resp.json['short_name'] == 'My Custom Org'[:12]
