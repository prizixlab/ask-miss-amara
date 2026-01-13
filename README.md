# Ms. Amara Tarot MVP

## Stack
- **Backend:** Flask
- **Database:** SQLAlchemy with SQLite by default (`app.db`), Postgres via `DATABASE_URL`
- **Templates:** Jinja2
- **Styling:** Plain CSS in `static/style.css`

## Local development
1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set environment variables (copy `.env.example` and export them in your shell):

```bash
cp .env.example .env
export $(grep -v '^#' .env | xargs)
```

3. Run the app:

```bash
python app.py
```

4. Visit `http://127.0.0.1:5000`.

## Admin workflow
- Navigate to `/admin` and enter `ADMIN_PASSWORD`.
- Create or edit tarot pulls by date (YYYY-MM-DD).
- The home page shows today's pull using America/New_York time.

## Production
Set `DATABASE_URL` to a Postgres connection string and configure `SESSION_SECRET` + `ADMIN_PASSWORD`.
