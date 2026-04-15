---
name: ojhunt-web
description: Web layer, PDF internals, API routes, running the dev server. Use when working on the FastAPI app, PDF features, or environment setup.
---

# Web Layer

## Running the dev server

Start as a background task with sandbox disabled (file watcher and loopback networking are
sandbox-blocked):

```bash
# Start (run_in_background: true, dangerouslyDisableSandbox: true)
uv run fastapi dev src/ojhunt/web/app.py --port 8080
```

- `curl` to localhost also requires `dangerouslyDisableSandbox: true`
- Background tasks don't persist between conversations — restart at the beginning of each session
- To free the port: `lsof -ti :8080 | xargs kill -9` (no sandbox bypass needed)
- Keep the server running after testing; the user will ask to stop it

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

## Project history context (for UI copy)

When writing UI copy that refers to "the old site":
- **Old site** = `github.com/Liu233w/acm-statistics` deployment (also known as *ACM Statistics*,
  *OJ Analyzer*, *OJHunt*)
- **Not** npuacm.info (built by Jiduo Zhang; unrelated to this codebase)
- VPS compromise: October 2025 — data after 2025-10-22 was lost
- `legacy.db` preserves history up to 2025-10-22; web + CLI export available
