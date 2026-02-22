"""
Moduł autentykacji – sesje oparte na tokenach w cookie.
Użytkownicy przechowywani w config/users.json (bcrypt hashe).
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Optional

USERS_PATH = Path(__file__).parent.parent / "config" / "users.json"
SESSION_COOKIE = "lem_session"
SESSION_TTL = 60 * 60 * 12  # 12 h

_sessions: dict[str, dict] = {}


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 200_000
    ).hex()


def _load_users() -> dict:
    if not USERS_PATH.exists():
        return {}
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def ensure_admin_exists() -> None:
    """Tworzy domyślne konto admin jeśli plik users.json jest pusty."""
    users = _load_users()
    if users:
        return
    default_pw = os.environ.get("LEM_ADMIN_PASSWORD", "lem2026!")
    add_user("admin", default_pw, role="admin")


def add_user(username: str, password: str, role: str = "user") -> bool:
    users = _load_users()
    if username in users:
        return False
    salt = secrets.token_hex(16)
    users[username] = {
        "password_hash": _hash_password(password, salt),
        "salt": salt,
        "role": role,
    }
    _save_users(users)
    return True


def verify_user(username: str, password: str) -> Optional[str]:
    """Zwraca rolę jeśli dane poprawne, None jeśli nie."""
    users = _load_users()
    entry = users.get(username)
    if not entry:
        return None
    expected = _hash_password(password, entry["salt"])
    if hmac.compare_digest(expected, entry["password_hash"]):
        return entry.get("role", "user")
    return None


def create_session(username: str, role: str) -> str:
    token = secrets.token_urlsafe(48)
    _sessions[token] = {
        "username": username,
        "role": role,
        "created": time.time(),
    }
    return token


def get_session(token: str) -> Optional[dict]:
    sess = _sessions.get(token)
    if not sess:
        return None
    if time.time() - sess["created"] > SESSION_TTL:
        _sessions.pop(token, None)
        return None
    return sess


def delete_session(token: str) -> None:
    _sessions.pop(token, None)


def list_users() -> list[dict]:
    users = _load_users()
    return [
        {"username": u, "role": d.get("role", "user")}
        for u, d in users.items()
    ]


def delete_user(username: str) -> bool:
    users = _load_users()
    if username not in users:
        return False
    del users[username]
    _save_users(users)
    return True


def change_password(username: str, new_password: str) -> bool:
    users = _load_users()
    if username not in users:
        return False
    salt = secrets.token_hex(16)
    users[username]["password_hash"] = _hash_password(new_password, salt)
    users[username]["salt"] = salt
    _save_users(users)
    return True


def change_role(username: str, new_role: str) -> bool:
    users = _load_users()
    if username not in users:
        return False
    users[username]["role"] = new_role
    _save_users(users)
    return True
