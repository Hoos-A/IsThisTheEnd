#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CERT_PATH="${API_SSL_CERT:-$ROOT_DIR/.certs/dev-cert.pem}"
CURL_FLAGS=("-s")
if [[ -f "$CERT_PATH" ]]; then
  CURL_FLAGS+=("--cacert" "$CERT_PATH")
else
  CURL_FLAGS+=("--insecure")
fi

echo "# health"
curl "${CURL_FLAGS[@]}" https://localhost:8000/health || true
echo

echo "# HSC 03.03A"
curl "${CURL_FLAGS[@]}" "https://localhost:8000/search?q=03.03A" || true
echo

echo "# DX pharyngitis"
curl "${CURL_FLAGS[@]}" "https://localhost:8000/search?q=pharyngitis" || true
echo
