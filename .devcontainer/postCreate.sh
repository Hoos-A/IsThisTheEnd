#!/usr/bin/env bash
set -euo pipefail

chmod +x /workspaces/IsThisTheEnd/run.sh || true
python3 -m venv /workspaces/IsThisTheEnd/.venv
source /workspaces/IsThisTheEnd/.venv/bin/activate
pip install --upgrade pip
pip install -r /workspaces/IsThisTheEnd/api/requirements.txt
npm --prefix /workspaces/IsThisTheEnd/web install
cat <<'MSG'
🚀 Codespace ready.
- Upload CSVs to /workspaces/IsThisTheEnd/data/
- Set Codespaces secret OPENAI_API_KEY
- Run ./run.sh to start API + web.
MSG
