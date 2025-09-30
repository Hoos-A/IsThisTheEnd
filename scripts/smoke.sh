#!/usr/bin/env bash
set -euo pipefail

CA_CERT=".certs/dev-cert.pem"
CURL_OPTS=()
if [[ -f "$CA_CERT" ]]; then
  CURL_OPTS+=(--cacert "$CA_CERT")
fi

base_url="https://localhost:8000"

echo "# health"
curl -s "$base_url/health" "${CURL_OPTS[@]}" || true
echo

echo "# HSC 03.03A"
curl -s "$base_url/search?q=03.03A" "${CURL_OPTS[@]}" || true
echo

echo "# DX pharyngitis"
curl -s "$base_url/search?q=pharyngitis" "${CURL_OPTS[@]}" || true
echo
