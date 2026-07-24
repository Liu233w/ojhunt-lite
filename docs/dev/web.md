# Web layer

Internal reference for the FastAPI app, PDF handling, dev server, and frontend conventions.
For user-facing usage (production deployment, container, API endpoints) see
[`docs/web.md`](../web.md).

## Running the dev server

Use `doit.sh` — it starts the server, waits until it's ready, and manages the PID file:

```bash
# Start and wait until ready (dangerouslyDisableSandbox: true)
./doit.sh start

# Other tasks
./doit.sh status          # check if running, and on which port
./doit.sh kill            # stop the server
./doit.sh logs            # tail server log
./doit.sh reap            # kill orphaned servers whose worktree was removed
./doit.sh update-snapshots  # update visual regression snapshots
```

- All `doit.sh` commands require `dangerouslyDisableSandbox: true` (loopback networking + file watcher)
- Background tasks don't persist between conversations — restart at the beginning of each session
- `doit.sh start` is idempotent — safe to call if already running
- **Port depends on the checkout** (so several worktrees can run at once): the main checkout
  uses **8080**; a git worktree gets a **dynamic free port** — run `./doit.sh status` (or read
  `.doit/server.port`) to find it. Don't assume 8080 inside a worktree. See
  [ADR 0009](../adr/0009-parallel-worktree-dev-server.md).
- **Removing a worktree leaks its server.** `./doit.sh start` auto-reaps orphans whose
  worktree is gone (registry in the main checkout's `.doit/`); run `./doit.sh reap` to clean up
  on demand.
- e2e tests auto-discover the port (`OJHUNT_DEV_PORT` → `.doit/server.port` → 8080), so
  `./doit.sh test-e2e` / `test-visual` work in any worktree.

## PDF internals

- `extract_data(pdf_bytes)` returns `PdfEmbeddedData` — has `settings` and `history` only.
  It does **not** have a `snapshot`; the snapshot is never embedded in the PDF. Build one
  manually from history if needed.
- For page routes returning `application/pdf` on success and HTML on error: return explicit
  `Response(content=..., media_type="application/pdf")` or `HTMLResponse(...)` — do not use
  `response_class=HTMLResponse` on the decorator.
- When adding form-based page endpoints accessible to agents, document them in `llms.txt`.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LOGIN_USERNAME__<CRAWLER>` | For shared-account crawlers | Auth username (uppercase crawler name) |
| `LOGIN_PASSWORD__<CRAWLER>` | For shared-account crawlers | Auth password (uppercase crawler name) |
| `BUILD_TIME` | No | Build timestamp (Unix epoch or ISO), shown on About page |
| `GIT_COMMIT_SHA` | No | Git commit hash, used for source code link on About page |

Credentials go in `.env` (gitignored) — loaded automatically by `load_dotenv()` in
`src/ojhunt/web/app.py`. No need to `source .env` manually.

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
