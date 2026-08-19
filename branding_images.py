"""Validation and derived-asset generation for an uploaded organization logo.

Pure image processing: given uploaded bytes, produce validated/re-encoded
bytes and render whichever derived icon the caller asks for. Nothing here
touches a filesystem or a database -- the logo is stored as bytes on
OrganizationSettings (see models.py) and the icon variants are rendered on
demand by routes/branding.py, not pre-generated and written to disk.

That's a deliberate departure from the app's earlier design, which wrote the
logo and a fixed set of icon files to a local directory. That only works on a
host with a writable, *persistent* filesystem, and this app has now run into
both ways that assumption fails in practice: a Render disk that was declared
in render.yaml but incompatible with the free plan it was paired with, and
Vercel's serverless functions, which have no persistent disk at all -- not
misconfigured, categorically absent, on every plan. Storing the bytes as a
database column sidesteps the question entirely: it behaves identically on
Neon, on Render's existing managed Postgres, or on SQLite in local dev,
because none of those depend on the *application process* having durable
disk.

Ideal dimensions/upload limits (also surfaced to the admin in the settings
UI):
- Square image, 512x512 to 1024x1024 px -- big enough to stay sharp at every
  size this app actually renders it (a ~28px sidebar mark, a larger login-page
  mark), small enough to load instantly on a phone.
- PNG with a transparent background is recommended; JPEG and WEBP are also
  accepted.
- Max upload size: 2 MB.

Why re-encode rather than store the uploaded bytes as-is: a file can carry a
valid image header while smuggling something else after it (a "polyglot"
upload). Decoding it with Pillow and writing back out only the pixel data
keeps whatever isn't actually image content out of what gets stored and
later served back to every visitor.
"""
import io

from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_DIMENSION = 2048  # px, either side -- generous ceiling; recommended is 512-1024
MIN_DIMENSION = 32  # px, either side -- guards against near-empty pixel data
ALLOWED_FORMATS = {'PNG', 'JPEG', 'WEBP'}
_CONTENT_TYPE_FOR_FORMAT = {
    'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp',
}

_ICON_BG = (255, 255, 255, 255)  # neutral white -- works under any logo color

# Every derived-icon name a caller may ask render_icon() for, and the ratio
# of the canvas each fills. Maskable variants get extra safe-zone padding
# because the OS crops them to a shape (circle, squircle, ...) after the
# fact; apple-touch-icon has no transparency (iOS composites its own
# background) so it's flattened to RGB.
ICON_SPECS = {
    'icon-192': (192, 0.72, 'RGBA'),
    'icon-512': (512, 0.72, 'RGBA'),
    'icon-192-maskable': (192, 0.55, 'RGBA'),
    'icon-512-maskable': (512, 0.55, 'RGBA'),
    'apple-touch-icon': (180, 0.72, 'RGB'),
}
_FAVICON_SIZES = (16, 32, 48)


class LogoValidationError(ValueError):
    """Raised with a user-facing message when an uploaded file can't be
    accepted as a logo."""


def validate_and_reencode(file_storage):
    """Validate an uploaded logo and return (bytes, content_type) of the
    re-encoded image. Raises LogoValidationError with a message that's safe
    to flash straight to the admin."""
    file_storage.stream.seek(0, io.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise LogoValidationError('No file was selected.')
    if size > MAX_UPLOAD_BYTES:
        raise LogoValidationError(
            'That file is too large (%d KB). Please upload an image under %d MB.'
            % (size // 1024, MAX_UPLOAD_BYTES // (1024 * 1024))
        )

    try:
        image = Image.open(file_storage.stream)
        image.verify()  # structural check; Pillow requires reopening to decode pixels afterwards
    except (UnidentifiedImageError, OSError, ValueError):
        raise LogoValidationError('That file is not a valid image.')

    file_storage.stream.seek(0)
    image = Image.open(file_storage.stream)
    fmt = (image.format or '').upper()
    if fmt not in ALLOWED_FORMATS:
        raise LogoValidationError('Please upload a PNG, JPEG, or WEBP image.')

    width, height = image.size
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise LogoValidationError(
            'That image is too large (%dx%dpx). Please upload something no '
            'larger than %dx%dpx.' % (width, height, MAX_DIMENSION, MAX_DIMENSION)
        )
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise LogoValidationError('That image is too small to use as a logo.')

    # Re-encode from decoded pixel data only -- see module docstring.
    image = image.convert('RGB') if fmt == 'JPEG' else image.convert('RGBA')
    buf = io.BytesIO()
    save_kwargs = {'quality': 92} if fmt == 'JPEG' else {}
    image.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue(), _CONTENT_TYPE_FOR_FORMAT[fmt]


def _centered_square(image, canvas_size, content_ratio):
    """`image` scaled to fit within content_ratio of canvas_size, centered on
    an opaque canvas_size x canvas_size white square."""
    canvas = Image.new('RGBA', (canvas_size, canvas_size), _ICON_BG)
    target = max(1, int(canvas_size * content_ratio))
    fitted = image.convert('RGBA').copy()
    fitted.thumbnail((target, target), Image.Resampling.LANCZOS)
    offset = ((canvas_size - fitted.width) // 2, (canvas_size - fitted.height) // 2)
    canvas.paste(fitted, offset, fitted)
    return canvas


def render_icon(logo_bytes, variant):
    """Render one derived icon (see ICON_SPECS for the valid names) from the
    stored logo bytes, as PNG bytes. Raises KeyError for an unknown variant
    -- callers should treat that as a 404, not retry."""
    canvas_size, content_ratio, mode = ICON_SPECS[variant]
    image = Image.open(io.BytesIO(logo_bytes))
    icon = _centered_square(image, canvas_size, content_ratio)
    if mode == 'RGB':
        icon = icon.convert('RGB')
    buf = io.BytesIO()
    icon.save(buf, format='PNG')
    return buf.getvalue()


def render_favicon(logo_bytes):
    """Render the multi-resolution .ico from the stored logo bytes."""
    image = Image.open(io.BytesIO(logo_bytes))
    frames = [_centered_square(image, s, content_ratio=0.8) for s in _FAVICON_SIZES]
    buf = io.BytesIO()
    frames[0].save(
        buf, format='ICO',
        sizes=[(s, s) for s in _FAVICON_SIZES], append_images=frames[1:],
    )
    return buf.getvalue()
