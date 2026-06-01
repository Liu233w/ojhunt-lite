#!/bin/bash
# Local dev task runner — see https://github.com/gnat/doit.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.doit"
mkdir -p "$RUN_DIR"

SERVER_PID="$RUN_DIR/server.pid"
SERVER_LOG="$RUN_DIR/server.log"
SERVER_PORTFILE="$RUN_DIR/server.port"
DEFAULT_PORT=8080

# A linked git worktree has a `.git` *file* (a gitdir pointer); the main checkout
# has a `.git` *directory*. Worktrees get a dynamic port so several can run at once
# without colliding on 8080.
is-worktree() { [[ -f "$ROOT_DIR/.git" ]]; }

# Central registry of running servers, kept in the *main* checkout's .doit/ so it
# survives removal of any linked worktree — the source of orphaned servers. Format:
# one TSV line per server: <pid>\t<port>\t<worktree-root>
#
# Resolve the main checkout's root by parsing the worktree's `.git` pointer file
# (`gitdir: <main>/.git/worktrees/<name>`) rather than shelling out to git, which
# can fail with "dubious ownership" when the checkout and the running user differ.
main-root() {
  is-worktree || { echo "$ROOT_DIR"; return; }
  local gitdir
  gitdir="$(sed -n 's/^gitdir: //p' "$ROOT_DIR/.git")"
  [[ -n "$gitdir" ]] || { echo "$ROOT_DIR"; return; }
  case "$gitdir" in /*) ;; *) gitdir="$ROOT_DIR/$gitdir" ;; esac
  # gitdir = <main>/.git/worktrees/<name> → main root is three levels up
  ( cd "$gitdir/../../.." 2>/dev/null && pwd ) || echo "$ROOT_DIR"
}
REGISTRY="$(main-root)/.doit/servers.tsv"

# Port this checkout's server runs on. Recorded by `start`; defaults to 8080 when
# no server has been started here (legacy behaviour for the main checkout).
current-port() {
  if [[ -f "$SERVER_PORTFILE" ]]; then cat "$SERVER_PORTFILE"; else echo "$DEFAULT_PORT"; fi
}

# Parse the port uvicorn actually bound from its startup log line:
#   "Uvicorn running on http://127.0.0.1:<port> (Press CTRL+C to quit)"
# We *observe* the port uvicorn chose rather than pre-allocating one. Pre-allocating
# (bind to port 0 in the script, close, then hand the number to fastapi) races: the
# freed port can be taken by another process — e.g. a parallel worktree's start — in
# the gap before fastapi rebinds it.
parse-port-from-log() {
  sed -nE 's#.*Uvicorn running on https?://[^:]+:([0-9]+).*#\1#p' "$SERVER_LOG" | tail -1
}

is-alive() { [[ -f "$1" ]] && command kill -0 "$(cat "$1")" 2>/dev/null; }
server-ready() { curl -s -o /dev/null "http://localhost:$(current-port)/"; }

evict-port() {
  local port="$1" pids
  pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
  [[ -z "$pids" ]] && return 0
  echo "Port ${port} was occupied by pid ${pids//$'\n'/, } — killing before starting server."
  # shellcheck disable=SC2086
  command kill -TERM $pids 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    sleep 0.3
    pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
    [[ -z "$pids" ]] && return 0
  done
  # shellcheck disable=SC2086
  command kill -KILL $pids 2>/dev/null || true
  sleep 0.2
}

register-server() {  # <pid> <port>
  mkdir -p "$(dirname "$REGISTRY")"
  printf '%s\t%s\t%s\n' "$1" "$2" "$ROOT_DIR" >>"$REGISTRY"
}

deregister-server() {  # drop this checkout's entries
  [[ -f "$REGISTRY" ]] || return 0
  local tmp; tmp="$(mktemp)"
  awk -F'\t' -v root="$ROOT_DIR" '$3 != root' "$REGISTRY" >"$tmp" && mv "$tmp" "$REGISTRY"
}

# Kill servers whose worktree directory no longer exists (git has no
# worktree-removal hook, so we clean up opportunistically here) and prune dead
# entries. Runs automatically before `start`; also exposed as a task.
reap() {
  [[ -f "$REGISTRY" ]] || return 0
  local tmp; tmp="$(mktemp)"
  local pid port wt
  while IFS=$'\t' read -r pid port wt || [[ -n "${pid:-}" ]]; do
    [[ -z "${pid:-}" ]] && continue
    if [[ ! -d "$wt" ]]; then
      if command kill -0 "$pid" 2>/dev/null; then
        pkill -TERM -P "$pid" 2>/dev/null || true
        command kill -TERM "$pid" 2>/dev/null || true
        echo "reaped orphaned server pid ${pid} (port ${port}) — worktree gone: ${wt}"
      fi
      continue  # drop entry
    fi
    command kill -0 "$pid" 2>/dev/null || continue  # dead pid — drop entry
    printf '%s\t%s\t%s\n' "$pid" "$port" "$wt" >>"$tmp"  # still alive — keep
  done <"$REGISTRY"
  mv "$tmp" "$REGISTRY"
}

start() {
  reap
  if is-alive "$SERVER_PID"; then
    echo "server already running (pid $(cat "$SERVER_PID")) on port $(current-port)"
    return 0
  fi
  rm -f "$SERVER_PID" "$SERVER_PORTFILE"
  # Main checkout keeps the stable 8080 (evict a stale holder first); a git worktree
  # asks uvicorn for a free port (--port 0) so several worktrees can run at once.
  local port_arg=$DEFAULT_PORT
  if is-worktree; then
    port_arg=0
  else
    evict-port "$DEFAULT_PORT"
  fi
  # `>` truncates the log, so parse-port-from-log only ever sees this run's line.
  ( cd "$ROOT_DIR" && exec uv run fastapi dev src/ojhunt/web/app.py --port "$port_arg" ) \
    >"$SERVER_LOG" 2>&1 &
  local pid=$!
  echo "$pid" >"$SERVER_PID"
  echo "server starting (pid $pid)..."
  # Discover the port uvicorn actually bound (race-free — no pre-allocation gap).
  local port=""
  for _ in $(seq 1 100); do
    if ! command kill -0 "$pid" 2>/dev/null; then
      echo "server exited during startup — see $SERVER_LOG" >&2
      rm -f "$SERVER_PID"
      return 1
    fi
    port="$(parse-port-from-log)"
    [[ -n "$port" ]] && break
    sleep 0.3
  done
  if [[ -z "$port" ]]; then
    echo "could not determine server port within timeout — see $SERVER_LOG" >&2
    pkill -TERM -P "$pid" 2>/dev/null || true
    command kill -TERM "$pid" 2>/dev/null || true
    rm -f "$SERVER_PID"
    return 1
  fi
  echo "$port" >"$SERVER_PORTFILE"
  register-server "$pid" "$port"
  echo "server started (pid $pid) — waiting for port $port..."
  until server-ready; do
    command kill -0 "$pid" 2>/dev/null || {
      echo "server exited before becoming ready — see $SERVER_LOG" >&2
      rm -f "$SERVER_PID" "$SERVER_PORTFILE"
      deregister-server
      return 1
    }
    sleep 0.3
  done
  echo "server ready on http://localhost:$port — logs: $SERVER_LOG"
}

kill() {
  if [[ ! -f "$SERVER_PID" ]]; then
    echo "server not running"
    deregister-server
    return 0
  fi
  local pid; pid="$(cat "$SERVER_PID")"
  if command kill -0 "$pid" 2>/dev/null; then
    pkill -TERM -P "$pid" 2>/dev/null || true
    command kill -TERM "$pid" 2>/dev/null || true
    echo "server killed (pid ${pid})"
    rm -f "$SERVER_PID" "$SERVER_PORTFILE"
    deregister-server
  elif ps -p "$pid" >/dev/null 2>&1; then
    local owner; owner="$(ps -o user= -p "$pid" | tr -d ' ')"
    echo "server: pid ${pid} is alive but owned by '${owner}' — run as ${owner} to stop it. Pid file kept." >&2
    return 1
  else
    echo "server not running (stale pid file)"
    rm -f "$SERVER_PID" "$SERVER_PORTFILE"
    deregister-server
  fi
}

status() {
  if is-alive "$SERVER_PID"; then
    echo "server: running (pid $(cat "$SERVER_PID")) on port $(current-port)"
  else
    echo "server: stopped"
  fi
}

logs() { tail -F "$SERVER_LOG"; }

lint() {
  ( cd "$ROOT_DIR" && uv run ruff check . )
}

test-unit() {
  ( cd "$ROOT_DIR" && uv run pytest -m "not network and not playwright" "$@" )
}

test-e2e() {
  if ! server-ready && ! is-alive "$SERVER_PID"; then
    echo "Starting server for e2e tests..."
    start
  fi
  ( cd "$ROOT_DIR" && OJHUNT_DEV_PORT="$(current-port)" uv run pytest -m playwright tests/e2e/ --ignore=tests/e2e/test_visual.py "$@" )
}

test-visual() {
  if ! server-ready && ! is-alive "$SERVER_PID"; then
    echo "Starting server for snapshot capture..."
    start
  fi
  rm -rf "$ROOT_DIR/test-results"
  ( cd "$ROOT_DIR" && OJHUNT_DEV_PORT="$(current-port)" uv run pytest -m playwright tests/e2e/test_visual.py "$@" )
}

test-crawler() {
  local name="${1:?usage: ./doit.sh test-crawler <crawler-name> [pytest-args...]}"
  shift
  local test_file="$ROOT_DIR/tests/crawlers/${name}_test.py"
  if [[ ! -f "$test_file" ]]; then
    echo "error: no test file found for crawler '${name}' (looked for tests/crawlers/${name}_test.py)" >&2
    return 1
  fi
  ( cd "$ROOT_DIR" && uv run pytest "$test_file" "$@" )
}

update-snapshots() {
  if ! server-ready && ! is-alive "$SERVER_PID"; then
    echo "Starting server for snapshot capture..."
    start
  fi
  echo "Updating visual snapshots..."
  rm -rf "$ROOT_DIR/test-results"
  ( cd "$ROOT_DIR" && OJHUNT_DEV_PORT="$(current-port)" uv run pytest tests/e2e/test_visual.py --update-snapshots "$@" )
  echo "Done — commit tests/e2e/__snapshots__/ alongside the change that required the update."
}

help() {
  cat <<EOF
Usage: ./doit.sh <task> [args...]

Server:
  start              start the dev server (waits until ready)
                     main checkout → port $DEFAULT_PORT; git worktree → a free port (recorded in .doit/server.port)
  kill               stop the server
  status             show if server is running and on which port
  logs               tail server log
  reap               kill orphaned servers whose git worktree has been removed

Tests:
  lint               run ruff linter
  test-unit          run unit tests (no network, no playwright) [pytest-args...]
  test-e2e           run e2e tests excluding visual (starts server if needed) [pytest-args...]
  test-visual        run visual regression tests (starts server if needed) [pytest-args...]
  test-crawler NAME  run tests for a specific crawler by name [pytest-args...]
  update-snapshots   update visual regression snapshots (starts server if needed)
EOF
}

[ "$#" -gt 0 ] || { help; exit 0; }
"$@"
