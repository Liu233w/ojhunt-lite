# Web Interface

## Running the Server

**Development** (with auto-reload):
```bash
uv run fastapi dev web/app.py --port 8080
```

**Production** (multi-worker):
```bash
uv run fastapi run web/app.py --port 8080 --workers 4
```

The web interface is available at http://127.0.0.1:8080

## Credentials for Login-Required Crawlers

Set environment variables before starting the server:

```bash
LOGIN_USERNAME__VJUDGE=user LOGIN_PASSWORD__VJUDGE=pass uv run fastapi dev web/app.py --port 8080
```

Or use a `.env` file (loaded automatically):
```
LOGIN_USERNAME__VJUDGE=...
LOGIN_PASSWORD__VJUDGE=...
LOGIN_USERNAME__CSES=...
LOGIN_PASSWORD__CSES=...
```

## Container

Pre-built images are available at `ghcr.io/liu233w/ojhunt-lite`.

```bash
# Start web server on port 8080
podman run -p 8080:8080 ghcr.io/liu233w/ojhunt-lite

# With VJudge credentials
podman run -p 8080:8080 \
  -e LOGIN_USERNAME__VJUDGE=user \
  -e LOGIN_PASSWORD__VJUDGE=pass \
  ghcr.io/liu233w/ojhunt-lite
```

> Replace `podman` with `docker` if preferred.

## API

Interactive API documentation is available at:

- **Swagger UI**: http://127.0.0.1:8080/docs
- **ReDoc**: http://127.0.0.1:8080/redoc

Example requests:

```bash
# List all available crawlers
curl http://127.0.0.1:8080/api/crawlers/

# Query a user on a specific platform
curl http://127.0.0.1:8080/api/crawlers/codeforces/tourist
```
