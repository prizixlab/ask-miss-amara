#!/usr/bin/env bash
set -euo pipefail
export AUTH_BYPASS=1
export ENFORCE_RATE_LIMIT=0
export DATABASE_URL=""
# export OPENAI_API_KEY=sk-PASTE-YOUR-REAL-KEY   # uncomment or set in your shell profile
python app.py
