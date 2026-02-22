"""
Moduł zarządzania promptami z wersjonowaniem.
Obsługuje ładowanie, zapisywanie i aktywację wersji promptów.
Wspiera per-competency prompty (aktywna wersja per moduł + per kompetencja).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"
MODULES = ["parse", "map", "score", "feedback"]
DEFAULT_COMPETENCY = "delegowanie"


def _get_module_dir(module: str) -> Path:
    if module not in MODULES:
        raise ValueError(f"Nieznany moduł: {module}. Dostępne: {MODULES}")
    return PROMPTS_DIR / module


def _load_meta(module: str) -> dict:
    meta_path = _get_module_dir(module) / "_meta.json"
    if not meta_path.exists():
        return {
            "module": module,
            "description": "",
            "active": {},
            "versions": [],
        }
    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Backward compat: jeśli active jest stringiem, konwertuj na dict
    if isinstance(data.get("active"), str):
        old_active = data["active"]
        data["active"] = {DEFAULT_COMPETENCY: old_active}

    return data


def _save_meta(module: str, meta: dict) -> None:
    meta_path = _get_module_dir(module) / "_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def _resolve_active_version(meta: dict, competency: str = DEFAULT_COMPETENCY) -> Optional[str]:
    """Zwraca aktywną wersję promptu dla danej kompetencji.
    Fallback: jeśli brak wersji per kompetencja, zwraca domyślną (delegowanie).
    """
    active = meta.get("active", {})
    if isinstance(active, str):
        return active
    if isinstance(active, dict):
        return active.get(competency) or active.get(DEFAULT_COMPETENCY)
    return None


def list_modules() -> list[dict]:
    """Zwraca listę modułów z ich aktywnymi wersjami."""
    result = []
    for module in MODULES:
        meta = _load_meta(module)
        result.append({
            "module": module,
            "description": meta.get("description", ""),
            "active": meta.get("active"),
            "version_count": len(meta.get("versions", [])),
        })
    return result


def list_versions(module: str) -> list[dict]:
    """Zwraca listę wersji dla danego modułu."""
    meta = _load_meta(module)
    active = meta.get("active", {})
    versions = []
    for v in meta.get("versions", []):
        is_active_for = []
        if isinstance(active, dict):
            for comp, ver in active.items():
                if ver == v["name"]:
                    is_active_for.append(comp)
        elif isinstance(active, str) and active == v["name"]:
            is_active_for.append(DEFAULT_COMPETENCY)

        versions.append({
            **v,
            "is_active": len(is_active_for) > 0,
            "active_for": is_active_for,
        })
    return versions


def get_prompt(module: str, version: Optional[str] = None, competency: str = DEFAULT_COMPETENCY) -> dict:
    """Pobiera treść promptu. Jeśli version=None, zwraca aktywną wersję dla danej kompetencji."""
    meta = _load_meta(module)

    if version is None:
        version = _resolve_active_version(meta, competency)

    if not version:
        raise ValueError(f"Brak aktywnej wersji dla modułu {module}, kompetencja {competency}")

    prompt_path = _get_module_dir(module) / f"{version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Nie znaleziono promptu: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()

    version_info = next(
        (v for v in meta.get("versions", []) if v["name"] == version),
        {"name": version, "description": "", "created_at": None}
    )

    return {
        "module": module,
        "version": version,
        "competency": competency,
        "content": content,
        "description": version_info.get("description", ""),
        "created_at": version_info.get("created_at"),
        "is_active": version == _resolve_active_version(meta, competency),
    }


def get_active_prompt_content(module: str, competency: str = DEFAULT_COMPETENCY) -> str:
    """Zwraca tylko treść aktywnego promptu (do użycia w pipeline)."""
    return get_prompt(module, competency=competency)["content"]


def save_prompt(
    module: str,
    version_name: str,
    content: str,
    description: str = "",
    activate: bool = False,
    competency: str = DEFAULT_COMPETENCY,
) -> dict:
    """Zapisuje nową wersję promptu."""
    module_dir = _get_module_dir(module)
    module_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = module_dir / f"{version_name}.txt"
    is_new = not prompt_path.exists()

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(content)

    meta = _load_meta(module)

    now = datetime.utcnow().isoformat() + "Z"

    existing = next(
        (v for v in meta.get("versions", []) if v["name"] == version_name),
        None
    )

    if existing:
        existing["description"] = description
        existing["updated_at"] = now
    else:
        if "versions" not in meta:
            meta["versions"] = []
        meta["versions"].append({
            "name": version_name,
            "description": description,
            "created_at": now,
        })

    if not isinstance(meta.get("active"), dict):
        meta["active"] = {}

    if activate or not meta["active"].get(competency):
        meta["active"][competency] = version_name

    _save_meta(module, meta)

    return {
        "module": module,
        "version": version_name,
        "competency": competency,
        "is_new": is_new,
        "activated": activate or meta["active"].get(competency) == version_name,
    }


def activate_version(module: str, version_name: str, competency: str = DEFAULT_COMPETENCY) -> dict:
    """Ustawia wersję jako aktywną dla danej kompetencji."""
    meta = _load_meta(module)

    version_exists = any(
        v["name"] == version_name for v in meta.get("versions", [])
    )

    if not version_exists:
        raise ValueError(f"Wersja {version_name} nie istnieje w module {module}")

    prompt_path = _get_module_dir(module) / f"{version_name}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Plik promptu nie istnieje: {prompt_path}")

    if not isinstance(meta.get("active"), dict):
        meta["active"] = {}

    old_active = meta["active"].get(competency)
    meta["active"][competency] = version_name
    _save_meta(module, meta)

    return {
        "module": module,
        "competency": competency,
        "old_active": old_active,
        "new_active": version_name,
    }


def get_active_versions(competency: str = None) -> dict:
    """Zwraca aktywne wersje. Jeśli competency podane, tylko dla tej kompetencji."""
    result = {}
    for module in MODULES:
        meta = _load_meta(module)
        active = meta.get("active", {})
        if competency:
            if isinstance(active, dict):
                result[module] = active.get(competency) or active.get(DEFAULT_COMPETENCY)
            else:
                result[module] = active
        else:
            result[module] = active
    return result
