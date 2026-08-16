# Web Interface

## Running the Server

**Development** (with auto-reload):
```bash
uv run fastapi dev src/ojhunt/web/app.py --port 8080
```

**Production** (multi-worker):
```bash
uv run fastapi run src/ojhunt/web/app.py --port 8080 --workers 4
```

The web interface is available at http://127.0.0.1:8080

## Credentials for Login-Required Crawlers

Set environment variables before starting the server:

```bash
LOGIN_USERNAME__VJUDGE=user LOGIN_PASSWORD__VJUDGE=pass uv run fastapi dev src/ojhunt/web/app.py --port 8080
```

Or use a `.env` file (loaded automatically):
```
LOGIN_USERNAME__VJUDGE=...
LOGIN_PASSWORD__VJUDGE=...
LOGIN_USERNAME__CSES=...
LOGIN_PASSWORD__CSES=...
```

## Identifying Your Instance

Every OJHunt request to an online judge carries a `User-Agent` and an `X-OJHunt` header that
name this project and link to its repository. If you run your own instance, set
`OJHUNT_INSTANCE_URL` to its public URL:

```
OJHUNT_INSTANCE_URL=https://oj.example.com
```

The URL is then added to both headers. A judge maintainer who wants a rate limit, or wants
you to stop, can then reach **you** instead of the upstream project. The value must be an
absolute `http://` or `https://` URL. The server refuses to start on a malformed one.

Only the web server reads `.env`. To identify the same instance when you run the CLI, export
the variable instead:

```bash
export OJHUNT_INSTANCE_URL=https://oj.example.com
uv run ojhunt tourist@codeforces
```

## Container

Pre-built images are available at `ghcr.io/liu233w/ojhunt-lite`. The same image also supports CLI mode — see [docs/cli.md](cli.md) for details.

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
