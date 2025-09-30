#!/usr/bin/env bash
set -euo pipefail

echo "# health"
curl -s http://localhost:8000/health || true
echo

echo "# HSC 03.03A"
curl -s "http://localhost:8000/search?q=03.03A" || true
echo

echo "# DX pharyngitis"
curl -s "http://localhost:8000/search?q=pharyngitis" || true
echo
