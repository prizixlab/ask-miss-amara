#!/usr/bin/env bash
set -euo pipefail
# In production, set DATABASE_URL, ADMIN_PASSWORD, SESSION_SECRET, PORT.
exec gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT:-8000} app:app
