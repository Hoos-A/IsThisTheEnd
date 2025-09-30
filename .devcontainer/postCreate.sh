#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${CODESPACE_VSCODE_FOLDER:-$(pwd)}"
RUNNER="$ROOT_DIR/run.sh"
PYTHON_BIN="${PYTHON:-python3}"
PY_ENV="$ROOT_DIR/.venv"
WEB_DIR="$ROOT_DIR/web"
API_DIR="$ROOT_DIR/api"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python binary '$PYTHON_BIN' not found. Install Python 3.11+ in the devcontainer image." >&2
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1; then
import ssl
PY
then
  echo "Python lacks SSL support; rebuild the Codespace or install libssl and recreate the environment." >&2
  exit 1
fi

echo "✅ Verified Python SSL support ($PYTHON_BIN)."

chmod +x "$RUNNER" || true

"$PYTHON_BIN" -m venv "$PY_ENV"
source "$PY_ENV/bin/activate"
pip install --upgrade pip
pip install -r "$API_DIR/requirements.txt"

deactivate

npm --prefix "$WEB_DIR" install

cat <<'MSG'
🚀 Codespace ready.
- Upload CSVs to /data (somb_extracted.csv, modifiers_extracted.csv, diagnostic_codes_extracted.csv)
- Set Codespaces secret OPENAI_API_KEY
- Run ./run.sh to start API + web
MSG
