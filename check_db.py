import sqlite3, json

db_path = "/home/kochnik/LEM/data/lem.db"
c = sqlite3.connect(db_path)

print("=== ASSESSMENTS: llm_model column ===")
rows = c.execute("SELECT id, participant_id, competency, llm_model FROM assessments ORDER BY id DESC").fetchall()
for r in rows:
    print(f"  id={r[0]} pid={r[1]!r} comp={r[2]} llm_model={r[3]!r}")

print("\n=== PIPELINE STEPS: checking for _llm data in output_data ===")
steps = c.execute("""
    SELECT id, assessment_id, step_name, output_data
    FROM pipeline_steps
    WHERE assessment_id IS NOT NULL
    ORDER BY id DESC
    LIMIT 20
""").fetchall()
for s in steps:
    try:
        data = json.loads(s[3]) if s[3] else {}
        llm = data.get("_llm", {})
        model = llm.get("model", "N/A") if llm else "no _llm"
        provider = llm.get("provider", "?") if llm else "?"
        print(f"  step_id={s[0]} assessment={s[1]} step={s[2]} provider={provider} model={model}")
    except:
        print(f"  step_id={s[0]} assessment={s[1]} step={s[2]} [parse error]")

print("\n=== CURRENT LLM RUNTIME (via API) ===")
import requests
sess = requests.Session()
r = sess.post("http://localhost:8010/api/auth/login", json={"username": "admin", "password": "lem2026!"})
if r.status_code == 200:
    r2 = sess.get("http://localhost:8010/api/llm/config")
    print(json.dumps(r2.json(), indent=2))
else:
    print("Login failed:", r.status_code)

c.close()
