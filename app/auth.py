"""
Moduł autentykacji – sesje oparte na tokenach w cookie.
Użytkownicy przechowywani w config/users.json (bcrypt hashe).
Sesje persystowane w config/sessions.json (współdzielone między workerami).
"""

import hashlib
import hmac
import json
import os
import secrets
import time
import fcntl
from pathlib import Path
from typing import Optional

USERS_PATH = Path(__file__).parent.parent / "config" / "users.json"
SESSIONS_PATH = Path(__file__).parent.parent / "config" / "sessions.json"
ACTIVITY_PATH = Path(__file__).parent.parent / "config" / "activity.json"
SESSION_COOKIE = "lem_session"
SESSION_TTL = 60 * 60 * 12  # 12 h
MAX_ACTIVITY_LOG = 1000


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 200_000
    ).hex()


def _load_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)
    tmp.replace(path)


def _load_users() -> dict:
    return _load_json(USERS_PATH, {})


def _save_users(users: dict) -> None:
    _save_json(USERS_PATH, users)


# ---------------------------------------------------------------------------
# Sessions (file-based, shared between workers)
# ---------------------------------------------------------------------------

def _load_sessions() -> dict:
    return _load_json(SESSIONS_PATH, {})


def _save_sessions(sessions: dict) -> None:
    _save_json(SESSIONS_PATH, sessions)


def _purge_expired(sessions: dict) -> dict:
    now = time.time()
    return {
        tok: s for tok, s in sessions.items()
        if now - s.get("created", 0) <= SESSION_TTL
    }


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
    sessions = _load_sessions()
    sessions = _purge_expired(sessions)
    sessions[token] = {
        "username": username,
        "role": role,
        "created": time.time(),
    }
    _save_sessions(sessions)
    return token


def get_session(token: str) -> Optional[dict]:
    sessions = _load_sessions()
    sess = sessions.get(token)
    if not sess:
        return None
    if time.time() - sess.get("created", 0) > SESSION_TTL:
        sessions.pop(token, None)
        _save_sessions(sessions)
        return None
    return sess


def delete_session(token: str) -> None:
    sessions = _load_sessions()
    if token in sessions:
        sessions.pop(token)
        _save_sessions(sessions)


# ---------------------------------------------------------------------------
# Activity log (file-based, shared between workers)
# ---------------------------------------------------------------------------

def log_activity(
    *,
    action: str,
    actor: Optional[str],
    target: Optional[str] = None,
    status: str = "ok",
    details: Optional[dict] = None,
) -> None:
    entry = {
        "ts": time.time(),
        "action": action,
        "actor": actor or "system",
        "target": target,
        "status": status,
        "details": details or {},
    }
    log = _load_json(ACTIVITY_PATH, [])
    if not isinstance(log, list):
        log = []
    log.append(entry)
    if len(log) > MAX_ACTIVITY_LOG:
        log = log[-MAX_ACTIVITY_LOG:]
    _save_json(ACTIVITY_PATH, log)


def list_activity(limit: int = 200) -> list[dict]:
    safe_limit = max(1, min(limit, MAX_ACTIVITY_LOG))
    log = _load_json(ACTIVITY_PATH, [])
    if not isinstance(log, list):
        return []
    return list(reversed(log[-safe_limit:]))


def list_active_sessions() -> list[dict]:
    sessions = _load_sessions()
    sessions = _purge_expired(sessions)
    now = time.time()
    result = []
    for _token, sess in sessions.items():
        age = now - sess.get("created", now)
        result.append(
            {
                "username": sess.get("username"),
                "role": sess.get("role", "user"),
                "created": sess.get("created"),
                "age_seconds": int(age),
            }
        )
    result.sort(key=lambda item: item.get("created", 0), reverse=True)
    return result


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
