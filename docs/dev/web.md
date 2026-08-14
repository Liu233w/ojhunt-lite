# Web layer operations

Running the dev server and configuring it. Code conventions for the web layer load
automatically from `.claude/rules/web.md` when you edit `src/ojhunt/web/`. For user-facing
usage (production deployment, container, API endpoints) see [`docs/web.md`](../web.md).

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

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LOGIN_USERNAME__<CRAWLER>` | For shared-account crawlers | Auth username (uppercase crawler name) |
| `LOGIN_PASSWORD__<CRAWLER>` | For shared-account crawlers | Auth password (uppercase crawler name) |
| `BUILD_TIME` | No | Build timestamp (Unix epoch or ISO), shown on About page |
| `GIT_COMMIT_SHA` | No | Git commit hash, used for source code link on About page |

Credentials go in `.env` (gitignored) — loaded automatically by `load_dotenv()` in
`src/ojhunt/web/app.py`. No need to `source .env` manually.
