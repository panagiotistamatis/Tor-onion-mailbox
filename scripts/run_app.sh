#!/usr/bin/env bash
# Run the FastAPI backend locally (bound to localhost only).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uvicorn app:app --host 127.0.0.1 --port 8000 --app-dir "$REPO_DIR/app"
