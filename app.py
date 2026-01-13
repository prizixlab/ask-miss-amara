import os
import uuid
from dataclasses import dataclass
from datetime import datetime, date
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import create_engine, text


EASTERN_TZ = ZoneInfo("America/New_York")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret")

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    ENGINE = create_engine("sqlite:///app.db", pool_pre_ping=True)


DDL = """
CREATE TABLE IF NOT EXISTS tarot_pulls (
  id TEXT PRIMARY KEY,
  pull_date DATE UNIQUE NOT NULL,
  deck_name TEXT NOT NULL,
  card_names TEXT NOT NULL,
  interpretation TEXT NOT NULL,
  image_url TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _bootstrap_schema() -> None:
    with ENGINE.begin() as cx:
        for stmt in DDL.split(";"):
            sql = stmt.strip()
            if sql:
                cx.execute(text(sql))


_bootstrap_schema()


@dataclass
class TarotPull:
    pull_date: str
    deck_name: str
    card_names: str
    interpretation: str
    image_url: str | None


@dataclass
class AdminFormState:
    data: TarotPull
    errors: dict


def _today_eastern() -> date:
    return datetime.now(EASTERN_TZ).date()


def _parse_date(date_str: str) -> date | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _get_pull_by_date(pull_date: date) -> TarotPull | None:
    with ENGINE.connect() as cx:
        row = cx.execute(
            text(
                """
                SELECT pull_date, deck_name, card_names, interpretation, image_url
                FROM tarot_pulls
                WHERE pull_date = :pull_date
                """
            ),
            {"pull_date": pull_date.isoformat()},
        ).mappings().first()
    if not row:
        return None
    return TarotPull(
        pull_date=row["pull_date"],
        deck_name=row["deck_name"],
        card_names=row["card_names"],
        interpretation=row["interpretation"],
        image_url=row["image_url"],
    )


def _list_pulls() -> list[TarotPull]:
    with ENGINE.connect() as cx:
        rows = cx.execute(
            text(
                """
                SELECT pull_date, deck_name, card_names, interpretation, image_url
                FROM tarot_pulls
                ORDER BY pull_date DESC
                """
            )
        ).mappings().all()
    return [
        TarotPull(
            pull_date=row["pull_date"],
            deck_name=row["deck_name"],
            card_names=row["card_names"],
            interpretation=row["interpretation"],
            image_url=row["image_url"],
        )
        for row in rows
    ]


def _save_pull(pull: TarotPull) -> None:
    with ENGINE.begin() as cx:
        cx.execute(
            text(
                """
                INSERT INTO tarot_pulls (
                    id, pull_date, deck_name, card_names, interpretation, image_url
                )
                VALUES (
                    :id, :pull_date, :deck_name, :card_names, :interpretation, :image_url
                )
                ON CONFLICT(pull_date) DO UPDATE SET
                    deck_name = excluded.deck_name,
                    card_names = excluded.card_names,
                    interpretation = excluded.interpretation,
                    image_url = excluded.image_url,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "pull_date": pull.pull_date,
                "deck_name": pull.deck_name,
                "card_names": pull.card_names,
                "interpretation": pull.interpretation,
                "image_url": pull.image_url,
            },
        )


@app.route("/")
def home():
    today = _today_eastern()
    pull = _get_pull_by_date(today)
    return render_template(
        "home.html",
        today=today.isoformat(),
        pull=pull,
    )


@app.route("/archive")
def archive():
    pulls = _list_pulls()
    return render_template("archive.html", pulls=pulls)


@app.route("/pull/<pull_date>")
def pull_detail(pull_date: str):
    parsed = _parse_date(pull_date)
    if not parsed:
        abort(404)
    pull = _get_pull_by_date(parsed)
    if not pull:
        return render_template("pull_detail.html", pull_date=pull_date, pull=None), 404
    return render_template("pull_detail.html", pull_date=pull_date, pull=pull)


@app.route("/about")
def about():
    return render_template("about.html")


def _admin_password() -> str | None:
    return os.environ.get("ADMIN_PASSWORD")


def _admin_logged_in() -> bool:
    return session.get("admin_authenticated", False)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    admin_password = _admin_password()
    if not admin_password:
        return render_template("admin_missing_password.html"), 500

    if not _admin_logged_in():
        if request.method == "POST":
            password = (request.form.get("password") or "").strip()
            if password == admin_password:
                session["admin_authenticated"] = True
                flash("Welcome back. You can edit pulls below.", "success")
                return redirect(url_for("admin"))
            flash("Incorrect password. Please try again.", "error")
        return render_template("admin_login.html")

    today = _today_eastern().isoformat()
    selected_date = request.args.get("date") or today
    existing_pull = _get_pull_by_date(_parse_date(selected_date)) if _parse_date(selected_date) else None

    form_data = TarotPull(
        pull_date=selected_date,
        deck_name=existing_pull.deck_name if existing_pull else "",
        card_names=existing_pull.card_names if existing_pull else "",
        interpretation=existing_pull.interpretation if existing_pull else "",
        image_url=existing_pull.image_url if existing_pull else "",
    )
    errors: dict[str, str] = {}

    if request.method == "POST":
        form_data = TarotPull(
            pull_date=(request.form.get("pull_date") or today).strip(),
            deck_name=(request.form.get("deck_name") or "").strip(),
            card_names=(request.form.get("card_names") or "").strip(),
            interpretation=(request.form.get("interpretation") or "").strip(),
            image_url=(request.form.get("image_url") or "").strip() or None,
        )

        if not _parse_date(form_data.pull_date):
            errors["pull_date"] = "Use YYYY-MM-DD format."
        if not form_data.deck_name:
            errors["deck_name"] = "Deck name is required."
        if not form_data.card_names:
            errors["card_names"] = "Card name(s) are required."
        if not form_data.interpretation:
            errors["interpretation"] = "Interpretation is required."

        if not errors:
            _save_pull(form_data)
            flash("Pull saved successfully.", "success")
            return redirect(url_for("admin", date=form_data.pull_date))

    pulls = _list_pulls()
    return render_template(
        "admin.html",
        form=AdminFormState(data=form_data, errors=errors),
        pulls=pulls,
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    flash("You are now logged out.", "info")
    return redirect(url_for("admin"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
