#!/bin/bash
set -e

cd /app

if [ $# -eq 0 ]; then
    exec uv run --no-sync fastapi run web/app.py --host 0.0.0.0 --port 8080
else
    exec uv run --no-sync ojhunt.py "$@"
fi
