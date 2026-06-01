# ADR 0009 — Parallel-Worktree Dev Server (Dynamic Port + Orphan Reaping)

**Status:** Accepted

## Context

`doit.sh` runs the local dev server on a fixed port (8080) with a single PID file under
`.doit/`. This breaks down when development happens in several git worktrees at once (e.g.
parallel agent jobs under `.claude/worktrees/`):

1. **Port collision** — a server started in one worktree holds 8080, so `./doit.sh start` in
   another worktree fails (or the eviction logic kills the *other* worktree's server).
2. **Orphaned-process leak** — if a worktree is removed (`git worktree remove`, or Claude
   Code's worktree cleanup, which calls it) while its server is still running, the process is
   orphaned: it keeps holding its port, and its `.doit/server.pid` vanishes with the
   directory, so nothing can stop it.

The e2e tests compounded the port problem: `tests/e2e/helpers.py` hard-coded
`BASE_URL = "http://localhost:8080"`, so tests could not target a server on any other port.

## Options Considered

### Port assignment

- **Deterministic per-path port (e.g. `9000 + hash(path) % 1000`).** Stable and predictable,
  but two worktrees can hash-collide onto the same port, reintroducing the collision.
- **Pre-allocate via `socket.bind(("", 0))` in the script, then pass the number to fastapi.**
  Rejected: this races. The script binds port 0, gets port N, *closes* the socket, and only
  later does `fastapi dev` bind N — and `uv run fastapi` takes a second or two to start. In
  that gap the OS can hand N to another process, which is most likely in exactly the target
  scenario (two `./doit.sh start` runs in parallel worktrees). If the rebind then fails, the
  start would hang.
- **`--port 0` to `fastapi dev`, then read the bound port from the uvicorn log (chosen).**
  uvicorn binds the ephemeral port itself and logs `Uvicorn running on http://127.0.0.1:<port>`
  with the *actual* port. We observe that — there is no pre-allocation gap, so no race.
  Verified that `fastapi dev --port 0` reports the real port (not `:0`), and that the listening
  socket lives in a grandchild process (so `lsof`-on-pid discovery is unreliable, but log
  parsing is exact and the message format is stable).

### Orphan cleanup

- **Git hook.** This was the first instinct, but git has *no worktree-removal hook* — hooks
  fire on commit/checkout/push, not on `git worktree remove`. Claude Code's `WorktreeRemove`
  setting-hook only applies to non-git isolation. So a hook cannot catch the case that
  produces the orphan.
- **Opportunistic reaper + registry (chosen).** A registry of running servers lives in the
  *main* checkout's `.doit/servers.tsv` (it survives removal of any linked worktree). A `reap`
  step kills any server whose worktree directory no longer exists and prunes dead entries. It
  runs automatically on every `start` and is exposed as `./doit.sh reap`.

## Decision

- **Main checkout keeps port 8080** (stable; matches `docs/web.md`, `README.md`, and habit).
- **Each git worktree launches `fastapi dev --port 0`**; the port uvicorn binds is read from
  its startup log and recorded in `.doit/server.port`. A worktree is detected by its `.git`
  being a *file* (a gitdir pointer) rather than a directory. `start` also fails fast (instead
  of hanging) if the server process exits before it becomes ready.
- **Tests resolve the port** from `OJHUNT_DEV_PORT` (exported by `doit.sh` test tasks),
  falling back to `.doit/server.port`, then `8080`.
- **Orphans are reaped opportunistically** via a central registry in the main checkout's
  `.doit/`, on `start` and on demand via `./doit.sh reap`.

The main checkout's root is resolved by parsing the worktree's `.git` pointer file
(`gitdir: <main>/.git/worktrees/<name>`) rather than shelling out to `git`, which fails with
"dubious ownership" when the checkout and the running user differ (e.g. an agent running as a
separate user).

## Consequences

- Several worktrees can run dev servers simultaneously without colliding; `./doit.sh status`
  reports the actual port.
- Removing a worktree no longer leaks a server forever — the next `./doit.sh start` (or an
  explicit `./doit.sh reap`) cleans it up. Cleanup is not instantaneous: the orphan lingers
  until the next reap.
- The registry is not locked; concurrent `start`/`reap` across worktrees could in principle
  race on the TSV file. Acceptable for single-user local dev.
- A direct `pytest` run (not via `doit.sh`) on a worktree still finds the right port through
  the `.doit/server.port` fallback; on the main checkout it defaults to 8080 as before.
