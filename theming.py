"""Derive a WCAG-AA-safe accent palette from a single admin-picked brand
color, for the organization-branding feature.

The design system already needs two different accent tokens -- one tuned to
be legible as *text* on the page background, another tuned to hold *white
text* as a button fill -- plus a lighter dark-mode variant of each (see the
token comments in static/css/app.css). Picking those by hand for an arbitrary
admin-chosen color isn't possible, and getting it wrong is exactly the bug
this codebase has hit more than once (a hue tuned for one role silently
failing contrast in the other). This module derives all of them
algorithmically and checks each one with the same real WCAG contrast math
used everywhere else, instead of trusting the picked color as-is.
"""
import colorsys
import re

HEX_RE = re.compile(r'^#?([0-9a-fA-F]{6})$')
WHITE = (255, 255, 255)

# The dark appearance's page/panel background that dark-mode accent TEXT sits
# on top of (see --bg-content in app.css). This is the binding constraint --
# --bg-window is even darker, which only makes contrast easier.
DARK_BG_CONTENT = (0x23, 0x23, 0x26)


def normalize_hex(value):
    """Return a '#rrggbb' string, or None if value isn't a valid 6-digit hex
    color (3-digit shorthand and named colors are intentionally rejected --
    this only ever comes from an <input type="color">, which always emits
    6-digit hex)."""
    if not value:
        return None
    m = HEX_RE.match(value.strip())
    if not m:
        return None
    return '#' + m.group(1).lower()


def hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(max(0, min(255, round(c))) for c in rgb))


def _linearize(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb):
    r, g, b = (_linearize(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb1, rgb2):
    """WCAG contrast ratio. Symmetric: the same number whichever of the two
    colors is "foreground" -- a shade dark enough to hold white text is, by
    this same math, dark enough to read as text on a white background."""
    l1, l2 = relative_luminance(rgb1), relative_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _hls(rgb):
    r, g, b = (c / 255 for c in rgb)
    return colorsys.rgb_to_hls(r, g, b)


def _from_hls(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r * 255, g * 255, b * 255)


def _round_rgb(rgb):
    return tuple(max(0, min(255, round(c))) for c in rgb)


def darken_for_contrast(rgb, target_rgb, min_ratio=4.5, step=0.01):
    """Walk HSL lightness down (hue/saturation held fixed) until `rgb`
    clears min_ratio against target_rgb, or bottoms out at black.

    Checks the *8-bit-rounded* candidate, not the raw float one -- rounding
    a float RGB that just barely passes down to hex can nudge its luminance
    just enough to fail again, which is exactly the kind of just-under-AA
    regression this codebase has hit before from a different angle (gradient
    stops, dark-mode fill tokens)."""
    h, l, s = _hls(rgb)
    while True:
        candidate = _round_rgb(_from_hls(h, l, s))
        if contrast_ratio(candidate, target_rgb) >= min_ratio or l <= 0.0:
            return rgb_to_hex(candidate)
        l = max(0.0, l - step)


def lighten_for_contrast(rgb, target_rgb, min_ratio=4.5, step=0.01):
    """As darken_for_contrast, but walking lightness up toward white."""
    h, l, s = _hls(rgb)
    while True:
        candidate = _round_rgb(_from_hls(h, l, s))
        if contrast_ratio(candidate, target_rgb) >= min_ratio or l >= 1.0:
            return rgb_to_hex(candidate)
        l = min(1.0, l + step)


def nudge_lightness(hex_color, delta):
    """A fixed HSL-lightness step, for hover states -- these are a transient
    affordance, not a resting state, so (matching this codebase's existing
    hand-authored hover tokens) they're a nudge off the base color rather
    than an independently contrast-verified shade."""
    rgb = hex_to_rgb(hex_color)
    h, l, s = _hls(rgb)
    l = min(1.0, max(0.0, l + delta))
    return rgb_to_hex(_from_hls(h, l, s))


def build_theme(base_hex):
    """Derive the light/dark accent token sets from one brand color.
    Returns None if base_hex isn't a valid hex color."""
    base_hex = normalize_hex(base_hex)
    if not base_hex:
        return None
    base_rgb = hex_to_rgb(base_hex)

    # The fill token must hold WHITE text at >=4.5:1. This is
    # appearance-independent (it only depends on hue/saturation vs. white),
    # so it's reused for --accent-fill in both light and dark -- matching
    # the hand-authored palette, where light mode's --accent and
    # --accent-fill are literally the same value for the same reason.
    fill_hex = darken_for_contrast(base_rgb, WHITE, min_ratio=4.5)
    fill_rgb = hex_to_rgb(fill_hex)

    light_accent_hex = fill_hex
    light_hover_hex = nudge_lightness(fill_hex, -0.08)
    light_soft = 'rgba({}, {}, {}, 0.11)'.format(*fill_rgb)

    # Dark-mode TEXT needs a much lighter tone than the fill -- lighten the
    # original brand color until it clears 4.5:1 against the dark content
    # background.
    dark_accent_hex = lighten_for_contrast(base_rgb, DARK_BG_CONTENT, min_ratio=4.5)
    dark_accent_rgb = hex_to_rgb(dark_accent_hex)
    dark_hover_hex = nudge_lightness(fill_hex, 0.12)
    dark_soft = 'rgba({}, {}, {}, 0.18)'.format(*dark_accent_rgb)

    return {
        'base': base_hex,
        'light': {
            'accent': light_accent_hex,
            'accent_fill': fill_hex,
            'accent_hover': light_hover_hex,
            'accent_soft': light_soft,
        },
        'dark': {
            'accent': dark_accent_hex,
            'accent_fill': fill_hex,
            'accent_hover': dark_hover_hex,
            'accent_soft': dark_soft,
        },
    }


def build_theme_css(base_hex):
    """A <style> body overriding the accent tokens for a custom brand color.
    Empty string if base_hex is invalid (falls back silently to the
    default palette already in app.css)."""
    theme = build_theme(base_hex)
    if not theme:
        return ''
    l, d = theme['light'], theme['dark']
    return (
        ':root, :root[data-appearance="light"] {\n'
        '  --accent: %(l_accent)s; --accent-fill: %(l_fill)s;\n'
        '  --accent-hover: %(l_hover)s; --accent-soft: %(l_soft)s;\n'
        '}\n'
        '@media (prefers-color-scheme: dark) {\n'
        '  :root:not([data-appearance="light"]) {\n'
        '    --accent: %(d_accent)s; --accent-fill: %(d_fill)s;\n'
        '    --accent-hover: %(d_hover)s; --accent-soft: %(d_soft)s;\n'
        '  }\n'
        '}\n'
        ':root[data-appearance="dark"] {\n'
        '  --accent: %(d_accent)s; --accent-fill: %(d_fill)s;\n'
        '  --accent-hover: %(d_hover)s; --accent-soft: %(d_soft)s;\n'
        '}\n'
    ) % {
        'l_accent': l['accent'], 'l_fill': l['accent_fill'],
        'l_hover': l['accent_hover'], 'l_soft': l['accent_soft'],
        'd_accent': d['accent'], 'd_fill': d['accent_fill'],
        'd_hover': d['accent_hover'], 'd_soft': d['accent_soft'],
    }
