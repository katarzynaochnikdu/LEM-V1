import urllib.request, json

url = "http://localhost:8010/api/health"
r = urllib.request.urlopen(url)
print("health:", r.read().decode())

# Login
login_data = json.dumps({"username": "admin", "password": "lem2026!"}).encode()
import http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req = urllib.request.Request("http://localhost:8010/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
r = opener.open(req)
print("login:", r.read().decode())

r = opener.open("http://localhost:8010/api/sessions")
sessions = json.loads(r.read().decode())
print(f"\nTotal: {len(sessions)} sessions")

groups = {}
for s in sessions:
    h = s.get("response_text_hash", "?")
    if h not in groups:
        groups[h] = []
    groups[h].append(s)

for h, items in groups.items():
    pids = sorted(set(i["participant_id"] for i in items))
    print(f"  hash={h} -> {len(items)} items, pids={pids}, text_len={items[0].get('response_text_len')}")
