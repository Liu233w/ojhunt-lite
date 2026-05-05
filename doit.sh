#!/bin/bash
# Local dev task runner — see https://github.com/gnat/doit.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.doit"
mkdir -p "$RUN_DIR"

SERVER_PID="$RUN_DIR/server.pid"
SERVER_LOG="$RUN_DIR/server.log"
SERVER_PORT=8080

is-alive() { [[ -f "$1" ]] && command kill -0 "$(cat "$1")" 2>/dev/null; }
server-ready() { curl -s -o /dev/null "http://localhost:${SERVER_PORT}/"; }

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

start() {
  if is-alive "$SERVER_PID"; then
    echo "server already running (pid $(cat "$SERVER_PID"))"
    return 0
  fi
  rm -f "$SERVER_PID"
  evict-port "$SERVER_PORT"
  ( cd "$ROOT_DIR" && exec uv run fastapi dev src/ojhunt/web/app.py --port "$SERVER_PORT" ) \
    >"$SERVER_LOG" 2>&1 &
  echo $! >"$SERVER_PID"
  echo "server started (pid $!) — waiting for port $SERVER_PORT..."
  until server-ready; do sleep 0.3; done
  echo "server ready — logs: $SERVER_LOG"
}

kill() {
  if [[ ! -f "$SERVER_PID" ]]; then
    echo "server not running"
    return 0
  fi
  local pid; pid="$(cat "$SERVER_PID")"
  if command kill -0 "$pid" 2>/dev/null; then
    pkill -TERM -P "$pid" 2>/dev/null || true
    command kill -TERM "$pid" 2>/dev/null || true
    echo "server killed (pid ${pid})"
    rm -f "$SERVER_PID"
  elif ps -p "$pid" >/dev/null 2>&1; then
    local owner; owner="$(ps -o user= -p "$pid" | tr -d ' ')"
    echo "server: pid ${pid} is alive but owned by '${owner}' — run as ${owner} to stop it. Pid file kept." >&2
    return 1
  else
    echo "server not running (stale pid file)"
    rm -f "$SERVER_PID"
  fi
}

status() {
  if is-alive "$SERVER_PID"; then
    echo "server: running (pid $(cat "$SERVER_PID")) on port $SERVER_PORT"
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
  ( cd "$ROOT_DIR" && uv run pytest -m playwright tests/e2e/ --ignore=tests/e2e/test_visual.py "$@" )
}

test-visual() {
  if ! server-ready && ! is-alive "$SERVER_PID"; then
    echo "Starting server for snapshot capture..."
    start
  fi
  ( cd "$ROOT_DIR" && uv run pytest -m playwright tests/e2e/test_visual.py "$@" )
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
  ( cd "$ROOT_DIR" && uv run pytest tests/e2e/test_visual.py --update-snapshots )
  echo "Done — commit tests/e2e/__snapshots__/ alongside the change that required the update."
}

help() {
  cat <<EOF
Usage: ./doit.sh <task> [args...]

Server:
  start              start the dev server on port $SERVER_PORT (waits until ready)
  kill               stop the server
  status             show if server is running
  logs               tail server log

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
