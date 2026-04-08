# Web

## PDF Internals

- `extract_data(pdf_bytes)` returns `PdfEmbeddedData` — has `settings` and `history` only. It does **not** have a `snapshot`; the snapshot is never embedded in the PDF. Build one manually from history if needed.
- For page routes returning `application/pdf` on success and HTML on error: return explicit `Response(content=..., media_type="application/pdf")` or `HTMLResponse(...)` — do not use `response_class=HTMLResponse` on the decorator.
- When adding form-based page endpoints accessible to agents, document them in `llms.txt`.

## Environment Variables

The web application accepts the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `LOGIN_USERNAME__<CRAWLER>` | For shared-account crawlers | Username for crawler authentication (uppercase crawler name) |
| `LOGIN_PASSWORD__<CRAWLER>` | For shared-account crawlers | Password for crawler authentication (uppercase crawler name) |
| `BUILD_TIME` | No | Build timestamp (Unix epoch or ISO format), shown on About page |
| `GIT_COMMIT_SHA` | No | Git commit hash, used to generate source code link on About page |

**Credentials** are stored in `.env` (gitignored) — loaded automatically by `load_dotenv()` in `src/ojhunt/web/app.py`, no need to `source .env` manually. Create `.env` if it doesn't exist and add entries for each login-required crawler:
```
LOGIN_USERNAME__<CRAWLER>=...
LOGIN_PASSWORD__<CRAWLER>=...
```

The user will need to fill the fields.
