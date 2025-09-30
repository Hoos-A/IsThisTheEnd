#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_ENV="$ROOT_DIR/.venv"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"

if [[ ! -d "$PY_ENV" ]]; then
  python3 -m venv "$PY_ENV"
fi
source "$PY_ENV/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r "$API_DIR/requirements.txt"

deactivate

if command -v npm >/dev/null 2>&1; then
  npm --prefix "$WEB_DIR" ci || npm --prefix "$WEB_DIR" install
else
  echo "npm not found. Please install Node.js 18+" >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "⚠️  OPENAI_API_KEY not set. Set Codespaces Secret OPENAI_API_KEY before running." >&2
fi

source "$PY_ENV/bin/activate"

(cd "$ROOT_DIR" && uvicorn api.main:app --host 0.0.0.0 --port 8000) &
API_PID=$!

(cd "$WEB_DIR" && npm run dev -- --host 0.0.0.0 --port 5173) &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID' EXIT

sleep 2

echo "API running at http://localhost:8000"
echo "Web UI running at http://localhost:5173"
echo "Press Ctrl+C to stop both services."

wait
