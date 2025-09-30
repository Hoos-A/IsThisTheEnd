#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_ENV="$ROOT_DIR/.venv"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"
CERT_DIR="$ROOT_DIR/.certs"
CERT_FILE="$CERT_DIR/dev-cert.pem"
KEY_FILE="$CERT_DIR/dev-key.pem"

log() {
  echo "[$(date '+%H:%M:%S')] $*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command '$1'." >&2
    exit 1
  fi
}

require_command python3
require_command openssl
require_command npm

log "Checking Python SSL support"
if ! python3 - <<'PY'
import ssl
print(ssl.OPENSSL_VERSION)
PY
then
  echo "Python ssl module missing. Reinstall Python 3.11 with OpenSSL support." >&2
  exit 1
fi

mkdir -p "$CERT_DIR"
if [[ ! -f "$CERT_FILE" || ! -f "$KEY_FILE" ]]; then
  log "Generating self-signed TLS certificate"
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 365 \
    -subj "/CN=localhost" >/dev/null 2>&1
fi

REQUIRED_CSVS=(
  "somb_extracted.csv"
  "modifiers_extracted.csv"
  "diagnostic_codes_extracted.csv"
)
DATA_DIR="$ROOT_DIR/data"
missing_files=()
for csv in "${REQUIRED_CSVS[@]}"; do
  if [[ ! -f "$DATA_DIR/$csv" ]]; then
    missing_files+=("$csv")
  fi
done
if (( ${#missing_files[@]} > 0 )); then
  echo "Missing CSV files: ${missing_files[*]}. Upload to $DATA_DIR." >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY not set. Add Codespaces secret OPENAI_API_KEY." >&2
  exit 1
fi

if [[ ! -d "$PY_ENV" ]]; then
  log "Creating Python virtual environment"
  python3 -m venv "$PY_ENV"
fi
source "$PY_ENV/bin/activate"
log "Installing Python dependencies"
pip install --upgrade pip >/dev/null
pip install -r "$API_DIR/requirements.txt" >/dev/null

deactivate

log "Installing Node dependencies"
npm --prefix "$WEB_DIR" ci >/dev/null || npm --prefix "$WEB_DIR" install >/dev/null

source "$PY_ENV/bin/activate"
export DEV_SSL_CERT="$CERT_FILE"
export DEV_SSL_KEY="$KEY_FILE"
export UVICORN_SSL_CERTFILE="$CERT_FILE"
export UVICORN_SSL_KEYFILE="$KEY_FILE"

log "Starting FastAPI (https://localhost:8000)"
(
  cd "$ROOT_DIR"
  uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-certfile "$CERT_FILE" \
    --ssl-keyfile "$KEY_FILE"
) &
API_PID=$!

log "Starting Vite dev server (https://localhost:5173)"
(
  cd "$WEB_DIR"
  npm run dev -- --host 0.0.0.0 --port 5173 --https --cert "$CERT_FILE" --key "$KEY_FILE"
) &
WEB_PID=$!

cleanup() {
  trap - EXIT INT TERM
  log "Shutting down services"
  kill "$API_PID" "$WEB_PID" >/dev/null 2>&1 || true
  wait "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 3

if command -v gp >/dev/null 2>&1; then
  gp preview --external 5173 >/dev/null 2>&1 || true
fi

log "API running at https://localhost:8000"
log "Web UI running at https://localhost:5173"
log "Press Ctrl+C to stop both services."

wait
