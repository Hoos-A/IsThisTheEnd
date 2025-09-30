# AHS Billing Assistant

This project delivers a microphone-first Alberta SOMB billing assistant that turns spoken encounters into citeable fee-code suggestions. The stack is FastAPI + WebSockets on the backend and React + Vite + Tailwind CSS on the frontend, packaged for one-command startup in GitHub Codespaces or any workstation with Python 3.11 and Node 18.

## ✨ Features

- 🎙️ **Mic-first capture** — stream audio to the backend over WebSockets, transcribe with Whisper, and show live partial/final transcripts.
- 🤖 **Structured extraction** — a tightly scoped GPT-4o mini prompt turns transcripts into problems, procedures, duration, setting, and visit hints.
- 📚 **CSV-only retrieval** — SOMB fees, modifiers, and ICD9 codes load from `/data/*.csv`, indexed in-memory for hybrid search without any database.
- 📐 **Deterministic rules** — place-of-service, duration, after-hours, and effective/expiry constraints annotate candidates before validation.
- ✅ **Validation + export** — review suggestions, run validation checks, and export final selections as CSV.
- 🔒 **Privacy aware** — no audio is stored; OpenAI credentials are read from environment secrets only.
- 🚀 **One command dev** — `./run.sh` provisions deps, ensures SSL, starts HTTPS backend/frontend, and opens the Codespaces preview.

## 📂 Repository layout

```
api/                      FastAPI backend (routers, services, rules)
web/                      React + Vite + Tailwind SPA
scripts/                  Utility helpers (smoke tests, samples)
.devcontainer/            Codespaces environment
.github/workflows/        Continuous integration
run.sh                    One-command runner (HTTPS)
README.md                 This guide
```

Upload the following CSVs to `./data/` (gitignored):

- `somb_extracted.csv`
- `modifiers_extracted.csv`
- `diagnostic_codes_extracted.csv`

Column names must match the spec in the project brief.

## 🚀 Quickstart

1. **Codespaces secrets** – add `OPENAI_API_KEY` under *Codespaces → Secrets* (or export in your shell locally).
2. **Upload CSVs** – drag the three required CSV files into `/data/` at the repo root.
3. **Launch**
   ```bash
   ./run.sh
   ```
4. **Test health**
   ```bash
   curl https://localhost:8000/health --cacert .certs/dev-cert.pem
   ```
5. **Open the UI** – use the Codespaces port 5173 preview or `https://localhost:5173` (trust the cert once).

## 🧪 Smoke tests

With the servers running:

```bash
./scripts/smoke.sh
```

Expected commands (after trusting the cert):

```
curl https://localhost:8000/health --cacert .certs/dev-cert.pem
curl "https://localhost:8000/search?q=03.03A" --cacert .certs/dev-cert.pem
curl "https://localhost:8000/search?q=pharyngitis" --cacert .certs/dev-cert.pem
```

## 🛠️ Development details

### Backend

- **Framework**: FastAPI (Python 3.11)
- **Key modules**:
  - `config.py` – environment-driven settings (OpenAI, data dir, providers).
  - `csv_store.py` – validates/loads CSVs into dictionaries and inverted indexes.
  - `routers/*` – REST & WebSocket endpoints (health, admin, search, LLM, streaming).
  - `services/llm` & `services/stt` – OpenAI integrations.
  - `retrieval/ranker.py` – token-based ranking with modifier/diagnosis attachment.
  - `rules/engine.py` – deterministic filters and validation helpers.

### Frontend

- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS (medical teal palette, focus-visible states)
- **Key components/pages**:
  - `LiveCoder` – microphone controls, transcript pane, entities, candidate table, validation/export.
  - `Admin` – dataset counts, CSV reload trigger.
  - `lib/audio.ts` – MediaRecorder helper for mic chunks.
  - `lib/ws.ts` – resilient WebSocket client with auto-reconnect.
  - `lib/useApiBase.ts` – resolves HTTPS API origin for localhost/GitHub.dev.

### Security & privacy

- Self-signed TLS certs generated locally in `.certs/` for HTTPS dev.
- Audio chunks are streamed and discarded (no persistence).
- OpenAI API key is never logged; startup fails fast if required providers lack credentials.

## 🧰 Devcontainer

The `.devcontainer` config installs Python 3.11 + Node 18, preloads dependencies in `postCreate.sh`, and reminds you to add CSVs and secrets. Rebuild the container if dependencies break.

## 📸 Screenshot

After the app starts, capture a screenshot via Codespaces preview and save to `/screenshots/launch.png` (not committed).

## 📜 License

MIT License. See `LICENSE`.
