# Miss Amara — Tarot MVP

A calm, minimalist tarot website for daily reflections.

## Local development
1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Set required environment variables:

   ```bash
   export SESSION_SECRET="replace-me"
   export ADMIN_PASSWORD="replace-me"
   ```

3. Run the app:

   ```bash
   python app.py
   ```

4. Visit `http://127.0.0.1:5000`.

## Admin access
- Visit `/admin` and enter the `ADMIN_PASSWORD` you set.
- Create or edit tarot pulls by date (YYYY-MM-DD).
- The home page displays today's pull using America/New_York time, or the most recent pull if today's is not yet available.

## Deploy later (production)
1. Provide a persistent database and set `DATABASE_URL` to a Postgres connection string.
2. Set secure secrets:

   ```bash
   export SESSION_SECRET="strong-random-value"
   export ADMIN_PASSWORD="strong-random-value"
   ```

3. Run with Gunicorn:

   ```bash
   gunicorn --bind 0.0.0.0:8000 app:app
   ```

4. Put a reverse proxy (NGINX, Render, Fly.io, etc.) in front to handle HTTPS.

## Notes
- No user accounts or payments are included.
- Images are optional and linked via URL in the admin form.
