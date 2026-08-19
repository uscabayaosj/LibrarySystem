# Brand assets

`seal.png` is the departmental seal of the Department of Anthropology, Ateneo
de Davao University. It is used here as this deployment's default logo and as
the source for the generated app-icon set in `static/icons/`.

**It is a trademark of the department, not part of this project's source
licence.** If you fork this repository for another institution, replace it —
either by swapping this file and regenerating the icons, or by uploading your
own logo through Admin → Settings, which validates, re-encodes, and rebuilds
the icon set for you without touching the repo.

The small-size brand mark is separate: it is the inline SVG `brand_mark()`
macro in `templates/_icons.html`, a 3x3 grid abstracted from the seal's own
portrait grid. The illustrated seal turns to mush below roughly 64px, so the
navigation rail and phone tab bar use the mark instead.
