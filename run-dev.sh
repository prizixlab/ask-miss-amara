#!/usr/bin/env bash
set -euo pipefail
export DATABASE_URL=""
export ADMIN_PASSWORD="dev-password"
export SESSION_SECRET="dev-secret"
python app.py
