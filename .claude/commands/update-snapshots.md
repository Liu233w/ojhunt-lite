---
description: Update visual regression snapshots for e2e tests
allowed-tools: Bash
---

Run `./doit.sh update-snapshots` with `dangerouslyDisableSandbox: true` (needs loopback networking).

The script starts the dev server automatically if it's not already running, runs the snapshot update, and prints a reminder to commit the results.

After it completes, commit `tests/e2e/__snapshots__/` alongside the change that required the update.
