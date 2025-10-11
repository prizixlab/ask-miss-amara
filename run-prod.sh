#!/usr/bin/env bash
set -euo pipefail
export AUTH_BYPASS=0
export ENFORCE_RATE_LIMIT=1
# In real prod, the platform will set these env vars:
#   DATABASE_URL, OPENAI_API_KEY, SESSION_SECRET, PORT
# Locally, PORT may be unset; default to 8000.
exec gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT:-8000} app:app
