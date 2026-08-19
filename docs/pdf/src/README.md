# PDF sources

The two PDFs in the parent directory are generated from the HTML in this
folder, rendered through headless Chromium's print engine.

| Output | Source | Audience |
|---|---|---|
| `library-system-deployment-runbook.pdf` | `runbook.html` | Whoever deploys and operates an instance |
| `library-system-overview.pdf` | `salesheet.html` | Prospective users evaluating the system |

`base.css` holds the shared print styling — it mirrors the app's own design
system (Fraunces, Archivo, and IBM Plex Mono loaded from `static/fonts`, the
department indigo `#292168`, hairline separators) so the documents look like
the product they describe. The cover-art swatches on the overview sheet are
generated with the app's own `cover_hue()`, so they show the real colours a
given ISBN produces rather than invented ones.

## Regenerating

```bash
pip install playwright
playwright install chromium
python render.py
```

Output goes to `docs/pdf/`. The script sets A4, prints backgrounds, and adds a
running footer with page numbers.

## Keeping the runbook accurate

`runbook.html` is a hand-formatted copy of the **Deployment runbook** section
of the top-level `README.md`, which remains the source of truth. When that
section changes, mirror the change here and re-render — the PDF does not
regenerate itself.

## Before sending the overview to anyone

`salesheet.html` ends with a contact block containing placeholders
(`Contact name`, `Email address`, `Phone`). Fill those in and re-render;
they are styled as dashed grey chips specifically so an unfilled one is
obvious on the page rather than shipping as a blank.
