import json, hashlib, secrets

users_path = "/home/kochnik/LEM/config/users.json"
with open(users_path) as f:
    users = json.load(f)

new_pw = "lem2026!"
salt = secrets.token_hex(16)
h = hashlib.pbkdf2_hmac("sha256", new_pw.encode(), salt.encode(), 200_000).hex()

users["admin"]["salt"] = salt
users["admin"]["password_hash"] = h
users["admin"]["role"] = "admin"

with open(users_path, "w", encoding="utf-8") as f:
    json.dump(users, f, indent=2, ensure_ascii=False)

print(f"Admin password reset to: {new_pw}")
print("Verifying...")

with open(users_path) as f:
    users2 = json.load(f)
h2 = hashlib.pbkdf2_hmac("sha256", new_pw.encode(), users2["admin"]["salt"].encode(), 200_000).hex()
print("Match:", h2 == users2["admin"]["password_hash"])

import requests
s = requests.Session()
r = s.post("http://localhost:8010/api/auth/login", json={"username": "admin", "password": new_pw})
print(f"Login test: {r.status_code} {r.text[:200]}")

if r.status_code == 200:
    r2 = s.get("http://localhost:8010/api/sessions")
    print(f"Sessions: {r2.status_code}")
    print(r2.text[:2000])
