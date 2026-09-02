"""Serves the uploaded organization logo and its derived icon set.

The logo is stored as bytes on OrganizationSettings (models.py), not as a
file on disk -- see branding_images.py's module docstring for why. The
derived icons (favicon, apple-touch-icon, the manifest's 'any'/'maskable'
variants) are rendered from those bytes on request rather than pre-generated
and stored, so there is exactly one row that can go stale, never a set of
files that can drift out of sync with it.

Every response here is safe to cache hard: the URL carries a ?v=<timestamp>
query param derived from logo_updated_at (see OrganizationSettings.icon_url
etc.), so a re-upload produces a new URL instead of invalidating an old one.
"""
from flask import Blueprint, Response, abort

from branding_images import ICON_SPECS, render_icon, render_favicon
from models import OrganizationSettings

bp = Blueprint('branding', __name__, url_prefix='/branding')

_CACHE_HEADERS = {'Cache-Control': 'public, max-age=31536000, immutable'}


def _require_logo():
    settings = OrganizationSettings.get(fresh=True)
    if not settings.logo_ready:
        abort(404)
    return settings


@bp.route('/logo')
def logo():
    settings = _require_logo()
    resp = Response(settings.logo_data, mimetype=settings.logo_content_type)
    resp.headers.update(_CACHE_HEADERS)
    return resp


@bp.route('/icon/<variant>.png')
def icon(variant):
    settings = _require_logo()
    if variant not in ICON_SPECS:
        abort(404)
    resp = Response(render_icon(settings.logo_data, variant), mimetype='image/png')
    resp.headers.update(_CACHE_HEADERS)
    return resp


@bp.route('/favicon.ico')
def favicon():
    settings = _require_logo()
    resp = Response(render_favicon(settings.logo_data), mimetype='image/vnd.microsoft.icon')
    resp.headers.update(_CACHE_HEADERS)
    return resp
