import io, re

P = "app.py"
src = io.open(P, "r", encoding="utf-8").read()

# --- replacement block for /daily route ---
replacement = '''@app.route("/daily")
def daily_view():
  gate = _ensure_login()
  if gate:
    return gate

  uid = session["user_id"]

  with ENGINE.begin() as cx:
    # Today's entry (if any)
    sql_today = (
      "SELECT aura_color, emotion, keywords, affirmation, created_at "
      "FROM daily_entries WHERE user_id=:u AND entry_date=CURRENT_DATE"
    )
    today = cx.execute(text(sql_today), {"u": uid}).mappings().first()

    # Recent 14 days of entries
    sql_hist = (
      "SELECT aura_color, emotion, keywords, affirmation, created_at, entry_date "
      "FROM daily_entries WHERE user_id=:u ORDER BY entry_date DESC LIMIT 14"
    )
    hist = cx.execute(text(sql_hist), {"u": uid}).mappings().all()

    # Recent rune draws (optional)
    sql_rune_hist = (
      "SELECT name, keywords, created_at, draw_date FROM daily_draws "
      "WHERE user_id=:u AND kind='rune' ORDER BY draw_date DESC LIMIT 10"
    )
    rune_hist = cx.execute(text(sql_rune_hist), {"u": uid}).mappings().all()

  return render_template("daily.html", today=today, hist=hist, rune_hist=rune_hist)
'''

# Replace from @app.route("/daily") through the next decorator or EOF
pat = r'(?ms)^@app\.route\("/daily"\)[\s\S]*?(?=^@app\.route\(|\Z)'
new, n = re.subn(pat, replacement + "\n", src)

if n == 0:
  print("Could not find daily_view() to patch. No changes made.")
  raise SystemExit(1)

io.open(P, "w", encoding="utf-8").write(new)
print("Patched daily_view() successfully.")
