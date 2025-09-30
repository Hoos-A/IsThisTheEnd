#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
PY_ENV="$ROOT_DIR/.venv"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python binary '$PYTHON_BIN' not found. Install Python 3.11+ and retry." >&2
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1; then
import ssl
PY
then
  cat >&2 <<'MSG'
Python was built without SSL support, so pip cannot reach PyPI.
Fix this by reinstalling Python with OpenSSL enabled (e.g., rebuild your Codespace, or install python3 + libssl-dev on Linux, or `brew install python@3.11` on macOS), then rerun ./run.sh.
See README.md for more details.
MSG
  exit 1
fi

echo "✅ Verified Python SSL support ($PYTHON_BIN)."

if [[ ! -d "$PY_ENV" ]]; then
  "$PYTHON_BIN" -m venv "$PY_ENV"
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

cleanup() {
  trap - EXIT INT TERM
  for pid in "$API_PID" "$WEB_PID"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
  wait "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 2

if ! kill -0 "$API_PID" >/dev/null 2>&1; then
  status=0
  if ! wait "$API_PID"; then
    status=$?
  fi
  echo "API process exited early. Check logs above for details." >&2
  exit $status
fi

if ! kill -0 "$WEB_PID" >/dev/null 2>&1; then
  status=0
  if ! wait "$WEB_PID"; then
    status=$?
  fi
  echo "Web process exited early. Check logs above for details." >&2
  exit $status
fi

echo "API running at http://localhost:8000"
echo "Web UI running at http://localhost:5173"
echo "Press Ctrl+C to stop both services."

while true; do
  if ! kill -0 "$API_PID" >/dev/null 2>&1; then
    status=0
    if ! wait "$API_PID"; then
      status=$?
    fi
    echo "API process exited (status $status). Shutting down." >&2
    exit $status
  fi
  if ! kill -0 "$WEB_PID" >/dev/null 2>&1; then
    status=0
    if ! wait "$WEB_PID"; then
      status=$?
    fi
    echo "Web process exited (status $status). Shutting down." >&2
    exit $status
  fi
  sleep 1
done
