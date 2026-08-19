# Bundled typefaces

These fonts are served by the app itself rather than from a CDN, so the
interface renders identically offline and on restricted campus networks. Only
the Latin subset of each is included, to keep the payload small.

| File | Family | Upstream | Licence |
|---|---|---|---|
| `fraunces-latin-300_800.woff2` | Fraunces (variable: `opsz`, `wght`, `SOFT`, `WONK`) | https://github.com/undercasetype/Fraunces | SIL Open Font License 1.1 — `OFL-fraunces.txt` |
| `archivo-latin-300_800.woff2` | Archivo (variable: `wght`, `wdth`) | https://github.com/Omnibus-Type/Archivo | SIL Open Font License 1.1 — `OFL-archivo.txt` |
| `plexmono-latin-400.woff2`, `plexmono-latin-600.woff2` | IBM Plex Mono | https://github.com/IBM/plex | SIL Open Font License 1.1 — `OFL-ibmplexmono.txt` |

The OFL permits redistribution provided the licence travels with the font
files, which is why the three licence texts sit alongside them here. None of
the families is renamed, so the Reserved Font Name clause is not engaged.

Roles are assigned in `static/css/app.css`: Fraunces carries page-level
display type, Archivo does the interface work, and IBM Plex Mono holds data —
accession codes, ISBNs, dates, and counts.
