import io, re

P = "app.py"
src = io.open(P, "r", encoding="utf-8").read()

replacement = '''@app.route("/daily/generate", methods=["POST"])
def daily_generate():
  gate = _ensure_login()
  if gate:
    return gate

  uid = session["user_id"]
  data = ai_aura()  # returns aura_color, emotion, keywords, affirmation

  # Upsert today's daily entry
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

  # Fetch recent draws history to display (optional)
  with ENGINE.begin() as cx:
    sql_tarot = (
      "SELECT * FROM daily_draws "
      "WHERE user_id=:u AND kind='tarot' AND draw_date=CURRENT_DATE"
    )
    sql_tarot_hist = (
      "SELECT name, keywords, created_at, draw_date FROM daily_draws "
      "WHERE user_id=:u AND kind='tarot' ORDER BY draw_date DESC LIMIT 10"
    )
    sql_rune_hist = (
      "SELECT name, keywords, created_at, draw_date FROM daily_draws "
      "WHERE user_id=:u AND kind='rune' ORDER BY draw_date DESC LIMIT 10"
    )

    tarot = cx.execute(text(sql_tarot), {"u": uid}).mappings().first()
    tarot_hist = cx.execute(text(sql_tarot_hist), {"u": uid}).mappings().all()
    rune_hist = cx.execute(text(sql_rune_hist), {"u": uid}).mappings().all()

  return jsonify({
    "ok": True,
    "aura": data,
    "tarot": tarot,
    "tarot_hist": tarot_hist,
    "rune_hist": rune_hist
  })
'''

# Replace from this decorator through the next decorator or EOF
pat = r'(?ms)^@app\.route\("/daily/generate",[^\n]*\)[\s\S]*?(?=^@app\.route\(|\Z)'
new, n = re.subn(pat, replacement + "\n", src)

if n == 0:
  print("Could not find daily_generate() to patch. No changes made.")
  raise SystemExit(1)

io.open(P, "w", encoding="utf-8").write(new)
print("Patched daily_generate() successfully.")
