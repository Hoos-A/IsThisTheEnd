#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
PY_ENV="$ROOT_DIR/.venv"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"
CERT_DIR="$ROOT_DIR/.certs"
DEFAULT_CERT="$CERT_DIR/dev-cert.pem"
DEFAULT_KEY="$CERT_DIR/dev-key.pem"

LLM_PROVIDER="${LLM_PROVIDER:-openai}"
STT_PROVIDER="${STT_PROVIDER:-openai}"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"
export DATA_DIR

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python binary '$PYTHON_BIN' not found. Install Python 3.11+ and retry." >&2
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1; then
import ssl
PY
  cat >&2 <<'MSG'
Python was built without SSL support, so pip cannot reach PyPI.
Fix this by reinstalling Python with OpenSSL enabled (e.g., rebuild your Codespace, or install python3 + libssl-dev on Linux, or `brew install python@3.11` on macOS), then rerun ./run.sh.
See README.md for more details.
MSG
  exit 1
fi

echo "✅ Verified Python SSL support ($PYTHON_BIN)."

if [[ "$LLM_PROVIDER" == "openai" || "$STT_PROVIDER" == "openai" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "⚠️  OPENAI_API_KEY not set. Set Codespaces Secret OPENAI_API_KEY before running." >&2
  fi
fi

REQUIRED_CSVS=(
  "somb_extracted.csv"
  "modifiers_extracted.csv"
  "diagnostic_codes_extracted.csv"
)
MISSING=()
for csv in "${REQUIRED_CSVS[@]}"; do
  if [[ ! -f "$DATA_DIR/$csv" ]]; then
    MISSING+=("$csv")
  fi
done

if (( ${#MISSING[@]} > 0 )); then
  echo "❌ Missing dataset files in $DATA_DIR:" >&2
  for file in "${MISSING[@]}"; do
    echo "   - $file" >&2
  done
  echo "Upload the CSVs listed in README.md before running the stack." >&2
  exit 1
fi

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

mkdir -p "$CERT_DIR"
API_CERT="${API_SSL_CERT:-$DEFAULT_CERT}"
API_KEY="${API_SSL_KEY:-$DEFAULT_KEY}"

if [[ ! -f "$API_CERT" || ! -f "$API_KEY" ]]; then
  if ! command -v openssl >/dev/null 2>&1; then
    echo "OpenSSL is required to generate a development certificate." >&2
    exit 1
  fi
  echo "🔐 Generating self-signed TLS certificate at $CERT_DIR" >&2
  openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$API_KEY" \
    -out "$API_CERT" \
    -subj "/C=CA/ST=Alberta/L=Edmonton/O=AHS Billing Assistant/OU=Dev/CN=localhost" >/dev/null 2>&1
fi

export API_SSL_CERT="$API_CERT"
export API_SSL_KEY="$API_KEY"
export DEV_SSL_CERT="$API_CERT"
export DEV_SSL_KEY="$API_KEY"

echo "🔒 TLS certificate: $API_CERT"

source "$PY_ENV/bin/activate"

(cd "$ROOT_DIR" && uvicorn api.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile "$API_SSL_KEY" --ssl-certfile "$API_SSL_CERT") &
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

open_browser() {
  local local_url="https://localhost:5173"
  if [[ -n "${CODESPACE_NAME:-}" ]] && command -v gp >/dev/null 2>&1; then
    echo "🌐 Opening Codespaces preview (port 5173)." >&2
    (gp preview --external 5173 >/dev/null 2>&1 &) || true
    echo "API running at https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
    echo "Web UI running at https://${CODESPACE_NAME}-5173.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
    return
  fi

  if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    ("$PYTHON_BIN" -m webbrowser "$local_url" >/dev/null 2>&1 &) || true
  fi
  echo "API running at https://localhost:8000"
  echo "Web UI running at $local_url"
}

open_browser
echo "Press Ctrl+C to stop both services."
echo "Health check: curl --cacert $API_SSL_CERT https://localhost:8000/health"

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
