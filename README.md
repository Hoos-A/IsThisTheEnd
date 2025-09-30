# AHS Billing Assistant

This repository implements a microphone-first Alberta SOMB billing assistant with a FastAPI backend and a Vite/Tailwind React frontend. It ingests doctor–patient conversations, extracts structured entities via OpenAI, searches CSV fee schedules, applies deterministic rules, and surfaces citeable billing suggestions for validation and export.

## Features

- 🎙️ **Mic-first capture** using WebSockets and Whisper transcription.
- 🤖 **LLM extraction** with a tight system prompt driving GPT-4o mini.
- 📁 **CSV-only storage** (no databases). All SOMB, modifier, and diagnostic datasets stay in-memory.
- 🔍 **Hybrid retrieval + rules** ranking candidates with transparent rationale and citations.
- ✅ **Validation** of place-of-service, effective dates, durations, and after-hours rules.
- 📤 **CSV export** for downstream billing systems.
- 🛡️ **Privacy-aware** by default: no audio persistence, environment-based secrets.
- 🧰 **One-command launch** via `./run.sh` for both API and web clients.

## Repository layout

```
api/                     FastAPI backend
web/                     React + Vite + Tailwind frontend
scripts/                 Utility scripts
.devcontainer/           Codespaces configuration
.github/workflows/       Continuous integration
run.sh                   One-shot runner
README.md                This file
```

Upload CSV data files to `/data/` (ignored by git):

- `somb_extracted.csv`
- `modifiers_extracted.csv`
- `diagnostic_codes_extracted.csv`

Column names must match the spec in the project prompt.

## Getting started

1. **Set secrets**
   - Add a Codespaces or environment secret named `OPENAI_API_KEY`.
2. **Upload CSV datasets**
   - Copy the three CSVs into `/data/`.
3. **Launch**
   ```bash
   ./run.sh
   ```
   The script installs dependencies (Python + Node) and starts the API on port 8000 and the web UI on port 5173.
4. **Use the app**
   - Open the browser (port 5173). Press **Record**, speak the encounter, watch transcript/entities/codes update live, run **Validate**, and **Export CSV**.

## Development

- **Backend**: FastAPI 0.1.0 app. Routers for health, admin, search, LLM suggestion, validation, and WebSocket streaming.
- **Frontend**: React 18 with Tailwind styling, accessible controls, resilient WebSocket client, and mic capture via MediaRecorder.
- **Scripts**:
  - `scripts/smoke.sh` – hit `/health` and sample search endpoints.
- **CI**: GitHub workflow runs backend lint/smoke (`uvicorn --version`) and frontend build (`vite build`).

### Troubleshooting

- **`ssl` module missing**: If `./run.sh` prints repeated warnings like `Can't connect to HTTPS URL because the SSL module is not available`, your Python installation was built without OpenSSL support. Rebuild the Codespace (recommended) or reinstall Python with SSL (for example, on Ubuntu: `sudo apt-get install python3 python3-venv libssl-dev` and recreate the virtualenv; on macOS: `brew install python@3.11`). Once `python3 -c "import ssl"` succeeds, rerun `./run.sh`.

## Environment variables

Backend configuration (via `api/config.py`):

| Variable            | Default         | Description                                      |
| ------------------- | --------------- | ------------------------------------------------ |
| `OPENAI_API_KEY`    | _required_      | OpenAI API key (Codespaces secret)               |
| `OPENAI_API_BASE`   | `https://api.openai.com/v1` | Optional alternate base URL           |
| `OPENAI_MODEL_STT`  | `whisper-1`     | Whisper model name                               |
| `OPENAI_MODEL_LLM`  | `gpt-4o-mini`   | Chat completion model                            |
| `STT_PROVIDER`      | `openai`        | Speech-to-text provider                          |
| `LLM_PROVIDER`      | `openai`        | LLM provider                                     |
| `DATA_DIR`          | `../data`       | Path to CSV directory                            |

Frontend configuration: copy `web/.env.example` to `web/.env` and set `VITE_API_BASE` if the API origin differs.

## Testing

With the servers running (e.g., via `./run.sh`), execute:

```bash
./scripts/smoke.sh
```

This checks `/health`, HSC lookup, and ICD search endpoints.

## Privacy & security

- Audio chunks are streamed live and discarded—no storage on disk.
- Only transcript text is sent to the LLM.
- Secrets remain outside source control and are never logged.

## Accessibility

- All interactive elements have keyboard focus styles and aria labels.
- Table headers stay visible while scrolling; text contrast meets WCAG AA.

## Continuous integration

`.github/workflows/ci.yml` ensures backend and frontend builds succeed on each push.

## License

This project is distributed under the MIT License. See `LICENSE` for details.
