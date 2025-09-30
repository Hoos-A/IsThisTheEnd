#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${CODESPACE_VSCODE_FOLDER:-$(pwd)}"
RUNNER="$ROOT_DIR/run.sh"
PY_ENV="$ROOT_DIR/.venv"
WEB_DIR="$ROOT_DIR/web"
API_DIR="$ROOT_DIR/api"

chmod +x "$RUNNER" || true

python3 -m venv "$PY_ENV"
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
