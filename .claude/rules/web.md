---
paths:
  - "src/ojhunt/web/**"
---

# Web layer conventions

Dev server lifecycle and environment variables are operational, not code conventions —
they live in [`docs/dev/web.md`](../../docs/dev/web.md). For user-facing usage see
[`docs/web.md`](../../docs/web.md).

## PDF internals

- `extract_data(pdf_bytes)` returns `PdfEmbeddedData` — has `settings` and `history` only.
  It does **not** have a `snapshot`; the snapshot is never embedded in the PDF. Build one
  manually from history if needed.
- For page routes returning `application/pdf` on success and HTML on error: return explicit
  `Response(content=..., media_type="application/pdf")` or `HTMLResponse(...)` — do not use
  `response_class=HTMLResponse` on the decorator.
- When adding form-based page endpoints accessible to agents, document them in `llms.txt`.

## Minimal JS principle

Keep JavaScript minimal. Business logic belongs in Python; JS handles only browser-specific
concerns.

- Day boundary / timezone computation → backend (frontend sends IANA timezone string)
- History merge/dedup → backend
- Pydantic schemas on all new API endpoints (not loose dicts)
- Prefer a POST to the server over inline JS computation

JS is appropriate for: reading local files, computing timezone name via
`Intl.DateTimeFormat().resolvedOptions().timeZone`, triggering downloads, reactive UI state.

## FastAPI trailing slashes + StaticFiles

When `StaticFiles` is mounted at `"/"`, FastAPI's `redirect_slashes` is suppressed.
`Mount("/")` matches every path first and returns 404 for paths that aren't real files —
the redirect never fires.

- `fetch()` URLs in `app.js` must exactly match the route path in `api.py` (no trailing
  slashes unless the route has one)
- HTML `href` attributes are harmless (browsers follow 307 redirects), but `fetch()` calls
  can silently fail because StaticFiles returns a non-JSON 404 body that breaks `response.json()`

## Reverse-proxy rate limiting (429)

The app itself never emits HTTP 429 — rate limiting is enforced by the production reverse
proxy, and its 429 body is **not** JSON. Any client `fetch` that reaches the server can
therefore receive a 429 with an HTML/plain-text body.

- Client `fetch` handlers must special-case `response.status === 429` **before** calling
  `response.json()` — otherwise the non-JSON body makes `response.json()` throw and the user
  sees a confusing parse error instead of a rate-limit message.
- Established guards live in `app.js`: `executeQuery`, `calculateReport`, `downloadReport`.

## CSS conventions

CSS files live at `src/ojhunt/web/static/assets/`:

| File | What belongs here |
|------|-------------------|
| `fonts.css` | `@font-face` blocks for the self-hosted IBM Plex, generated from the Google Fonts stylesheet. Never add a webfont via a CDN `<link>` — that reintroduces a third-party origin into the CSP and sends visitor IPs to it ([ADR 0010](../../docs/adr/0010-relaxed-csp-for-inline-alpine.md)) |
| `base.css` | Design-system tokens (`:root`, `[data-accent=...]`), page resets, `.topbar`, `.page`, `.header`, `.footer`, `dialog`/`.dlg-*`, `.card` base layout (including `::before` stripe and `:hover`), `[x-cloak]`, `:focus-visible`, responsive media queries for shared components |
| `index.css` | Everything used *only* by the home page: `.step`, `.report-slot`, `.grid`, card internals (`.c-hd`, `.c-body-row`, `.c-ft`, `.c-err-msg`, `.solved-link`, `.subs-val`, `.iconbtn`, `.loading-dots`, `.card-empty`), card status variants (`.card.r-ok::before` etc.), `.download-card`/`.summary`/`.dc-*`/`.stat`, `.composer`, `.field`, `.btn` (all variants), `.step-actions` |

**Short templates** (crawlers, about, pdf pages) keep their inline `<style>` blocks — only extract when a template's styles grow long.

**The critical rule:** anything from the original `base.html.jinja` `<style>` block that *any* page besides `index.html` uses must stay in `base.css`. The `about` page uses `.card`, `.card::before`, and `.card:hover` — these are in `base.css`.

**Referencing CSS in templates:**

```html
<link rel="stylesheet" href="/assets/base.css?v={{ static_version }}">
```

`static_version` is a Jinja2 global injected via `jinja_env.globals["static_version"] = STATIC_VERSION` in `pages.py` — no need to pass it in individual `.render()` calls.

**Visual regression tests** live in `tests/e2e/test_visual.py` (local-only, skipped in CI). After any CSS change:

```bash
# Update baselines (dangerouslyDisableSandbox: true)
./doit.sh update-snapshots

# Verify no unintended visual diff (dangerouslyDisableSandbox: true)
./doit.sh test-visual
```

Baselines are stored in `tests/e2e/__snapshots__/`. Commit baseline PNGs alongside the test or CSS change that necessitates them.

## Project history context (for UI copy)

When writing UI copy that refers to "the old site":
- **Old site** = `github.com/Liu233w/acm-statistics` deployment (also known as *ACM Statistics*,
  *OJ Analyzer*, *OJHunt*)
- **Not** npuacm.info (built by Jiduo Zhang; unrelated to this codebase)
- VPS compromise: October 2025 — data after 2025-10-22 was lost
- `legacy.db` preserves history up to 2025-10-22; web + CLI export available
