import httpx
import json

resp = httpx.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "Authorization": "Bearer 2iMU4Xgr4hhg80RLpQEZ0nHY1j7zNQ7CFkeKU1Z6lZHzyALuKU",
        "Content-Type": "application/json"
    },
    json={
        "model": "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
        "messages": [{"role": "user", "content": "Powiedz OK po polsku"}],
        "max_tokens": 20
    },
    timeout=30
)
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
