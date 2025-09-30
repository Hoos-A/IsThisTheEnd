#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspaces/$(basename "$PWD")"
VENV="$ROOT/.venv"

python3 -m venv "$VENV"
source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$ROOT/api/requirements.txt"
deactivate

npm --prefix "$ROOT/web" ci || npm --prefix "$ROOT/web" install

cat <<MSG
✅ Devcontainer ready
• Upload CSVs to $ROOT/data/
• Add Codespaces secret OPENAI_API_KEY
• Run ./run.sh to start HTTPS backend/frontend
MSG
