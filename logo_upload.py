"""Validation and storage for an uploaded organization logo.

Ideal dimensions/upload limits (also surfaced to the admin in the settings
UI):
- Square image, 512x512 to 1024x1024 px -- big enough to stay sharp at every
  size this app actually renders it (a ~28px sidebar mark, a larger login-page
  mark), small enough to load instantly on a phone.
- PNG with a transparent background is recommended; JPEG and WEBP are also
  accepted.
- Max upload size: 2 MB.

Why re-encode rather than save the uploaded bytes as-is: a file can carry a
valid image header while smuggling something else after it (a "polyglot"
upload). Decoding it with Pillow and writing back out only the pixel data
keeps whatever isn't actually image content out of what lands on disk.
"""
import os

from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_DIMENSION = 2048  # px, either side -- generous ceiling; recommended is 512-1024
MIN_DIMENSION = 32  # px, either side -- guards against near-empty pixel data
ALLOWED_FORMATS = {'PNG', 'JPEG', 'WEBP'}
_EXT_FOR_FORMAT = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp'}

_ICON_SIZES = (192, 512)
_FAVICON_SIZES = (16, 32, 48)
_ICON_BG = (255, 255, 255, 255)  # neutral white -- works under any logo color


class LogoValidationError(ValueError):
    """Raised with a user-facing message when an uploaded file can't be
    accepted as a logo."""


def validate_and_save(file_storage, upload_dir):
    """Validate an uploaded logo and save it as 'logo.<ext>' inside
    upload_dir, replacing any previously saved logo (this is a singleton
    setting, not a gallery -- there is only ever one current logo).

    Returns the saved filename (e.g. 'logo.png'). Raises LogoValidationError
    with a message that's safe to flash straight to the admin.
    """
    file_storage.stream.seek(0, os.SEEK_END)
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

    os.makedirs(upload_dir, exist_ok=True)
    # Clear any previously saved logo under a different extension, so
    # switching formats doesn't leave a stale file lying around alongside
    # the new one.
    for stale_ext in _EXT_FOR_FORMAT.values():
        stale_path = os.path.join(upload_dir, 'logo.%s' % stale_ext)
        if os.path.exists(stale_path):
            os.remove(stale_path)

    ext = _EXT_FOR_FORMAT[fmt]
    filename = 'logo.%s' % ext
    path = os.path.join(upload_dir, filename)
    save_kwargs = {'quality': 92} if fmt == 'JPEG' else {}
    image.save(path, format=fmt, **save_kwargs)

    _clear_generated_icons(upload_dir)
    generate_app_icons(image, upload_dir)
    return filename


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


def generate_app_icons(image, upload_dir):
    """Derive installed-app icons (favicon, apple-touch-icon, and the
    manifest's 'any'/'maskable' variants) from a validated logo image, so
    "Add to Home Screen" shows the organization's own mark instead of the
    library's default one.

    `image` should already be the re-encoded image validate_and_save
    produces -- this trusts it rather than re-validating.
    """
    for size in _ICON_SIZES:
        _centered_square(image, size, content_ratio=0.72).save(
            os.path.join(upload_dir, 'icon-%d.png' % size))
        # Maskable icons get cropped to a shape (circle, squircle, ...) by
        # the OS -- extra safe-zone padding keeps the logo from being clipped.
        _centered_square(image, size, content_ratio=0.55).save(
            os.path.join(upload_dir, 'icon-%d-maskable.png' % size))

    _centered_square(image, 180, content_ratio=0.72).convert('RGB').save(
        os.path.join(upload_dir, 'apple-touch-icon.png'))

    favicon_frames = [_centered_square(image, s, content_ratio=0.8) for s in _FAVICON_SIZES]
    favicon_frames[0].save(
        os.path.join(upload_dir, 'favicon.ico'), format='ICO',
        sizes=[(s, s) for s in _FAVICON_SIZES], append_images=favicon_frames[1:],
    )


def _clear_generated_icons(upload_dir):
    names = ['apple-touch-icon.png', 'favicon.ico']
    for size in _ICON_SIZES:
        names.append('icon-%d.png' % size)
        names.append('icon-%d-maskable.png' % size)
    for name in names:
        path = os.path.join(upload_dir, name)
        if os.path.exists(path):
            os.remove(path)
