import os, uuid, re
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, render_template_string, request, redirect, session, jsonify, url_for
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret")
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
   DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # Fallback to local SQLite on Render’s ephemeral disk (fine for now)
    ENGINE = create_engine("sqlite:///app.db", pool_pre_ping=True)
is_sqlite = ENGINE.url.get_backend_name() == "sqlite"

DDL = """
CREATE TABLE IF NOT EXISTS users(
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  subscription_status TEXT DEFAULT 'free',
  created_at TIMESTAMPTZ DEFAULT now() # Make Postgres-style DDL work on SQLite when needed

); 

CREATE TABLE IF NOT EXISTS questions(
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS answers(
  id UUID PRIMARY KEY,
  question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  affirmation TEXT,
  tags_csv TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS daily_entries(
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
  aura_color TEXT, emotion TEXT, keywords TEXT, affirmation TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (user_id, entry_date)
);
CREATE TABLE IF NOT EXISTS daily_draws(
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  draw_date DATE NOT NULL DEFAULT CURRENT_DATE,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  keywords TEXT, meaning TEXT, affirmation TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (user_id, kind, draw_date)
);
CREATE TABLE IF NOT EXISTS cards(
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  card_name TEXT NOT NULL, notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
# Make Postgres-style DDL work on SQLite when needed
DDL_SQL = (DDL
           .replace("UUID", "TEXT")
           .replace("TIMESTAMPTZ DEFAULT now()", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

ddl_to_run = DDL_SQL if is_sqlite else DDL

with ENGINE.begin() as conn:
    conn.execute(text(ddl_to_run))

def _ensure_login():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return None

def _now_utc():
    return datetime.now(timezone.utc)

TAROT_FILE_MAP = {
    "the fool":"0-the-fool.jpg","the magician":"1-the-magician.jpg","the high priestess":"2-the-high-priestess.jpg",
    "the empress":"3-the-empress.jpg","the emperor":"4-the-emperor.jpg","the hierophant":"5-the-hierophant.jpg",
    "the lovers":"6-the-lovers.jpg","the chariot":"7-the-chariot.jpg","strength":"8-strength.jpg",
    "the hermit":"9-the-hermit.jpg","wheel of fortune":"10-wheel-of-fortune.jpg","justice":"11-justice.jpg",
    "the hanged man":"12-the-hanged-man.jpg","death":"13-death.jpg","temperance":"14-temperance.jpg",
    "the devil":"15-the-devil.jpg","the tower":"16-the-tower.jpg","the star":"17-the-star.jpg",
    "the moon":"18-the-moon.jpg","the sun":"19-the-sun.jpg","judgement":"20-judgement.jpg","the world":"21-the-world.jpg",
}
RUNE_FILE_MAP = {
    "fehu":"fehu.svg","uruz":"uruz.svg","thurisaz":"thurisaz.svg","ansuz":"ansuz.svg","raidho":"raidho.svg",
    "kenaz":"kenaz.svg","gebo":"gebo.svg","wunjo":"wunjo.svg","hagalaz":"hagalaz.svg","nauthiz":"nauthiz.svg",
    "isa":"isa.svg","jera":"jera.svg","eihwaz":"eihwaz.svg","perthro":"perthro.svg","algiz":"algiz.svg",
    "sowilo":"sowilo.svg","tiwaz":"tiwaz.svg","berkano":"berkano.svg","ehwaz":"ehwaz.svg","mannaz":"mannaz.svg",
    "laguz":"laguz.svg","ingwaz":"ingwaz.svg","othala":"othala.svg","dagaz":"dagaz.svg",
}
def tarot_image_url(name:str|None):
    if not name: return None
    key = re.sub(r"\s+", " ", name.strip().lower())
    f = TAROT_FILE_MAP.get(key)
    return url_for("static", filename=f"cards/tarot/{f}") if f else None
def rune_image_url(name:str|None):
    if not name: return None
    key = re.sub(r"\s+", " ", name.strip().lower())
    f = RUNE_FILE_MAP.get(key)
    return url_for("static", filename=f"cards/runes/{f}") if f else None

def ai_oracle_response(question:str):
    api_key = os.environ.get("OPENAI_API_KEY")
    return (
  "Today's energy suggests gentle clarity. Name two hopes and one boundary. Trust your pacing.",
  "I am calmly guided",
  "clarity, pacing, trust",
)
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    system = ("You are Miss Amara, a compassionate tarot guide. Offer grounded, kind insights in plain language. "
              "Use metaphor sparingly. Never give medical/legal/financial advice. Encourage reflection and free will. "
              "At the top include an optional line 'Primary Card: <Name>' if one fits. "
              "End with one concise affirmation beginning with 'I am…' and 3 lowercase tags (comma-separated).")
    user = f"Question: {question}\nRespond in 3–5 short paragraphs, then provide an affirmation and tags."
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0.8
        )
        full = resp.choices[0].message.content.strip()
        affirmation = "I am centered and guided."
        tags = "reflection, guidance, calm"
        return (full, affirmation, tags)
    except Exception:
        return ("The oracle is quiet for a moment—please try again shortly.", "I am patient with the process.","retry, patience, process")

def ai_aura():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"aura_color":"lavender","emotion":"calm, receptive",
                "keywords":"intuition, stillness, trust",
                "affirmation":"I am gently aligned with my inner knowing."}
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    system=("You are Miss Amara. Create a daily aura with aura_color (CSS color words), emotion (few words), "
            "keywords (3–5, comma-separated), affirmation (starts with 'I am'). Return four labeled lines.")
    user="Generate today's aura."
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.8
    )
    out = resp.choices[0].message.content.strip()
    def grab(lbl):
        m = re.search(rf"{lbl}:\s*(.+)", out, re.I)
        return (m.group(1).strip() if m else "")
    return {"aura_color":grab("aura_color|Color|Aura Color"),
            "emotion":grab("emotion|Mood|Emotion"),
            "keywords":grab("keywords"),
            "affirmation":grab("affirmation") or "I am centered and guided."}

def ai_draw(kind:str, name_hint:str|None):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        if kind=="tarot":
            return {"name":name_hint or "The High Priestess","keywords":"intuition, stillness, inner voice",
                    "meaning":"Quiet your mind; answers arrive when you stop chasing.",
                    "affirmation":"I am guided by calm inner knowing."}
        else:
            return {"name":name_hint or "Fehu","keywords":"beginnings, resources, flow",
                    "meaning":"Nurture what's already in your hands and let momentum grow.",
                    "affirmation":"I am a steward of growing gifts."}
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    system=("You are Miss Amara, a gentle tarot/rune guide. Return exactly 4 labeled lines:\n"
            "Name: <card or rune>\nKeywords: <3–6 words>\nMeaning: <2–4 short sentences>\nAffirmation: I am ...")
    user=f"Type: {kind}\nName (optional): {name_hint or ''}\nCreate today's daily draw."
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.8
    )
    out = resp.choices[0].message.content.strip()
    def g(lbl):
        m = re.search(rf"{lbl}:\s*(.+)", out, re.I)
        return m.group(1).strip() if m else ""
    return {"name":g("Name") or (name_hint or f"Unknown {kind}"),
            "keywords":g("Keywords"),"meaning":g("Meaning"),
            "affirmation":g("Affirmation") or "I am centered and guided."}

@app.route("/")
def index():
    with ENGINE.begin() as cx:
        c = cx.execute(text("SELECT COUNT(*) FROM users")).scalar()
    return render_template("index.html", signup_count=c)

@app.route("/signup", methods=["POST"])
def signup():
    email = (request.form.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return redirect(url_for("index"))

    # For now we don’t touch the DB on signup; just create a session
    uid = str(uuid.uuid4())
    session["email"] = email
    session["user_id"] = uid

    return redirect(url_for("app_view"))

@app.route("/app")
def app_view():
    gate = _ensure_login()
    if gate:
        return gate

    uid = session["user_id"]

    with ENGINE.begin() as cx:
    sql_rows = (
        "SELECT "
        "q.id AS qid, "
        "q.content AS q, "
        "COALESCE(a.body,'') AS a, "
        "COALESCE(a.affirmation,'') AS aff, "
        "COALESCE(a.tags_csv,'') AS tags, "
        "q.created_at AS created "
        "FROM questions q "
        "LEFT JOIN answers a ON a.question_id = q.id "
        "WHERE q.user_id = :u "
        "ORDER BY q.created_at DESC "
        "LIMIT 20"
    )
    rows = cx.execute(text(sql_rows), {"u": uid}).mappings().all()

    sql_last = (
        "SELECT created_at "
        "FROM questions "
        "WHERE user_id = :u "
        "ORDER BY created_at DESC "
        "LIMIT 1"
    )
    last = cx.execute(text(sql_last), {"u": uid}).scalar()

return render_template("app.html", rows=rows, last=last)


    

    return render_template("app.html", rows=rows, last=last)


@app.route("/ask", methods=["POST"])
def ask():
    gate = _ensure_login()
    if gate: return gate
    uid = session["user_id"]
    data = request.get_json() or {}
    q = (data.get("question") or "").strip()
    if not q:
        return jsonify({"ok":False,"error":"empty_question"}), 400

    with ENGINE.begin() as cx:
        last = cx.execute(text("SELECT created_at FROM questions WHERE user_id=:u ORDER BY created_at DESC LIMIT 1"),
                          {"u":uid}).scalar()
        if last and (_now_utc() - last) < timedelta(hours=24):
            return jsonify({"ok":False,"error":"rate_limited"}), 429

        qid = str(uuid.uuid4())
        body, aff, tags = ai_oracle_response(q)
tags_csv = tags

with ENGINE.begin() as cx:
    aid = str(uuid.uuid4())
    sql = (
        "INSERT INTO answers (id, question_id, body, affirmation, tags_csv) "
        "VALUES (:id, :question_id, :body, :affirmation, :tags_csv)"
    )

    cx.execute(
        text(sql),
        {
            "id": aid,
            "question_id": qid,
            "body": body,
            "affirmation": aff,
            "tags_csv": tags_csv,
        },
    )

m = re.search(r"^Primary\s*Card:\s*(.+)$", body, re.I | re.M)
card_name = m.group(1).strip() if m else None
img = tarot_image_url(card_name) if card_name else None
return jsonify({"ok": True, "answer": body, "affirmation": aff, "tags": tags, "image": img})

@app.route("/daily")
def daily_view():
    gate = _ensure_login()
    if gate: return gate
    uid = session["user_id"]
    with ENGINE.begin() as cx:     
  sql_today = (
    "SELECT aura_color, emotion, keywords, affirmation, created_at "
    "FROM daily_entries WHERE user_id=:u AND entry_date=CURRENT_DATE"
  )
  today = cx.execute(text(sql_today), {"u": uid}).mappings().first()

  sql_hist = (
    "SELECT aura_color, emotion, keywords, affirmation, created_at, entry_date "
    "FROM daily_entries WHERE user_id=:u ORDER BY entry_date DESC LIMIT 14"
  )
  hist = cx.execute(text(sql_hist), {"u": uid}).mappings().all()


@app.route("/daily/generate", methods=["POST"])
def daily_generate():
    gate = _ensure_login()
    if gate: return gate
    uid = session["user_id"]
    data = ai_aura()
    with ENGINE.begin() as cx:
            sql = (
  "INSERT INTO daily_entries (id, user_id, entry_date, aura_color, emotion, keywords, affirmation) "
  "VALUES (:id, :u, CURRENT_DATE, :c, :e, :k, :a) "
  "ON CONFLICT (user_id, entry_date) DO UPDATE SET "
  "aura_color = :c, emotion = :e, keywords = :k, affirmation = :a, created_at = now()"
)
cx.execute(
  text(sql),
  {
    "id": str(uuid.uuid4()),
    "u": uid,
    "c": data["aura_color"],
    "e": data["emotion"],
    "k": data["keywords"],
    "a": data["affirmation"],
  },
)
    uid = session["user_id"]
    with ENGINE.begin() as cx:
        sql_tarot = (
  "SELECT * FROM daily_draws "
  "WHERE user_id=:u AND kind='tarot' AND draw_date=CURRENT_DATE"
)
sql_tarot_hist = (
  "SELECT name, keywords, created_at, draw_date FROM daily_draws "
  "WHERE user_id=:u AND kind='tarot' ORDER BY draw_date DESC LIMIT 10"
)
tarot = cx.execute(text(sql_tarot), {"u": uid}).mappings().first()
tarot_hist = cx.execute(text(sql_tarot_hist), {"u": uid}).mappings().all()

sql_rune_hist = (
  "SELECT name, keywords, created_at, draw_date FROM daily_draws "
  "WHERE user_id=:u AND kind='rune' ORDER BY draw_date DESC LIMIT 10"
)
rune_hist = cx.execute(text(sql_rune_hist), {"u": uid}).mappings().all()
    gate = _ensure_login()
    if gate: return gate
    uid = session["user_id"]
    name_hint = (request.form.get("name") or "").strip() or None
    
    with ENGINE.begin() as cx:
        
        sql = """
INSERT INTO daily_draws (id, user_id, draw_date, kind, name, keywords, meaning, affirmation)
VALUES (:id, :u, CURRENT_DATE, 'tarot', :n, :k, :m, :a)
ON CONFLICT (user_id, kind, draw_date) DO UPDATE SET
  name = :n, keywords = :k, meaning = :m, affirmation = :a, created_at = now()
"""

cx.execute(
    text(sql),
    {
        "id": str(uuid.uuid4()),
        "u": uid,
        "n": data["name"],
        "k": data["keywords"],
        "m": data["meaning"],
        "a": data["affirmation"],
    },
    )
    uid = session["user_id"]
    name_hint = (request.form.get("name") or "").strip() or None
    sql = (
  "INSERT INTO daily_draws (id, user_id, draw_date, kind, name, keywords, meaning, affirmation) "
  "VALUES (:id, :u, CURRENT_DATE, 'rune', :n, :k, :m, :a) "
  "ON CONFLICT (user_id, kind, draw_date) DO UPDATE SET "
  "name = :n, keywords = :k, meaning = :m, affirmation = :a, created_at = now()"
)
cx.execute(
  text(sql),
  {
    "id": str(uuid.uuid4()),
    "u": uid,
    "n": data["name"],
    "k": data["keywords"],
    "m": data["meaning"],
    "a": data["affirmation"],
  },
)
@app.route("/moon")
def moon_view():
    gate = _ensure_login()
    if gate: return gate
    today = datetime.now().date().isoformat()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        ritual = "Light a candle and name one intention you'll nourish this week."
    else:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        system=("You are Miss Amara. Provide one short ritual suggestion for today (1–2 sentences).")
        user=f"Today's date is {today}. Offer something gentle and universal."
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                temperature=0.7
            )
            ritual = resp.choices[0].message.content.strip()
        except Exception:
            ritual = "Breathe slowly for two minutes and release one worry on the exhale."
    return render_template("moon.html", today=today, ritual=ritual)

@app.route("/tracker")
def tracker_view():
    gate = _ensure_login()
    if gate: return gate
    # TODO: if you previously showed rows/top here, reinsert that logic
    # and pass them into the template.
    return render_template("tracker.html")
    uid = session["user_id"]
    name = (request.form.get("card_name") or "").strip()
    notes = (request.form.get("notes") or "").strip() or None
    if not name:
        return redirect(url_for("tracker_view"))
    with ENGINE.begin() as cx:
        cx.execute(
            text("INSERT INTO cards(id, user_id, card_name, notes) VALUES (:id,:u,:n,:t)"),
            {"id": str(uuid.uuid4()), "u": uid, "n": name, "t": notes},
        )
    return redirect(url_for("tracker_view"))
def list_images(folder):
    """
    Return image filenames located under static/<folder>.
    Example: folder="tarot" -> static/tarot/*.jpg
    """
    path = os.path.join(app.static_folder, folder)
    exts = (".png", ".jpg", ".jpeg", ".webp", ".gif")
    if not os.path.isdir(path):
        return []
    return sorted([f for f in os.listdir(path) if f.lower().endswith(exts)])

def pick_random(folder):
    files = list_images(folder)
    return random.choice(files) if files else None

def pick_daily(folder, seed_text):
    """Deterministic pick (e.g., 'card of the day'):
    same selection for the same seed_text for all users.
    """
    files = list_images(folder)
    if not files:
        return None
    seed = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    idx = int(seed, 16) % len(files)
    return files[idx]

@app.get("/daily/<kind>")  # /daily/tarot or /daily/runes
def daily_kind(kind):
    if kind not in ("tarot", "runes"):
        today = datetime.now().date().isoformat()
    today = datetime.date.today().isoformat()  # keeps same pick all day
    fn = pick_daily(kind, f"{kind}-{today}")
    img_url = url_for("static", filename=f"{kind}/{fn}") if fn else None
    return render_template("daily.html", kind=kind, image_url=img_url)

# Optional: simple JSON API if you want to redraw via JS without reload
@app.get("/api/draw/<kind>")
def api_draw(kind):
    if kind not in ("tarot", "runes"):
        return jsonify({"error": "Unknown kind"}), 400
    fn = pick_random(kind)
    return jsonify({"file": fn, "url": url_for("static", filename=f"{kind}/{fn}")})
# === END TAROT & RUNES ===
# --- ASK MISS AMARA (super minimal) ---
import os
from openai import OpenAI
from flask import request, jsonify

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post("/ask/<kind>")  # use /ask/tarot or /ask/runes
def ask_kind(kind):
    if kind not in ("tarot", "runes"):
        return jsonify({"error": "Unknown kind"}), 400

    question = (request.form.get("question") or "").strip()
    if not question:
        question = "Give a gentle, practical daily reading."

    system_msg = (
        "You are Miss Amara, a warm but grounded tarot/runes reader. "
        "Offer supportive, realistic guidance. 120–180 words, end with one practical action."
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"Modality: {kind}. Question: {question}"},
        ],
        temperature=0.8,
        max_tokens=300,
    )

    answer = resp.choices[0].message.content.strip()
    return jsonify({"answer": answer})
# --- END ASK MISS AMARA ---


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
