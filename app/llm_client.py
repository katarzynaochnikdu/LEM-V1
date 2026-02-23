"""
Centralny klient LLM - przełączanie między local-server i OpenAI API.
Konfiguracja persystowana do pliku JSON, żeby była współdzielona między workerami.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Literal
from openai import AsyncOpenAI

logger = logging.getLogger("lem.llm")

LlmProvider = Literal["local", "openai"]

_CONFIG_DIR = Path(__file__).parent.parent / "config"
_RUNTIME_PATH = _CONFIG_DIR / "llm_runtime.json"
_RUNTIME_CACHE_TTL = 2.0

_cached_runtime: dict | None = None
_cached_at: float = 0.0


def _env_default_provider() -> LlmProvider:
    value = os.getenv("LLM_PROVIDER", "local").strip().lower()
    return "openai" if value == "openai" else "local"


def _env_local_base_url() -> str:
    return os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8000/v1")


def _env_local_api_key() -> str:
    return os.getenv("LOCAL_LLM_API_KEY", "no-key")


def _env_local_model() -> str:
    return os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ")


def _env_openai_base_url() -> str:
    return os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")


def _env_openai_model() -> str:
    return os.getenv("OPENAI_API_MODEL", "gpt-4o")


def _supported_openai_models() -> list[str]:
    raw = os.getenv("OPENAI_SUPPORTED_MODELS", "gpt-4o,gpt-4.1")
    models = [item.strip() for item in raw.split(",") if item.strip()]
    return models or ["gpt-4o", "gpt-4.1"]


def _build_runtime_from_env() -> dict:
    return {
        "provider": _env_default_provider(),
        "local": {
            "base_url": _env_local_base_url(),
            "api_key": _env_local_api_key(),
            "model": _env_local_model(),
        },
        "openai": {
            "base_url": _env_openai_base_url(),
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": _env_openai_model(),
        },
    }


def _save_runtime(runtime: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    safe = {
        "provider": runtime["provider"],
        "local": {"base_url": runtime["local"]["base_url"], "model": runtime["local"]["model"]},
        "openai": {"base_url": runtime["openai"]["base_url"], "model": runtime["openai"]["model"]},
    }
    if runtime["openai"].get("api_key"):
        safe["openai"]["api_key"] = runtime["openai"]["api_key"]
    try:
        tmp = _RUNTIME_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(safe, indent=2), encoding="utf-8")
        tmp.replace(_RUNTIME_PATH)
    except OSError:
        logger.warning("Could not persist LLM runtime to %s", _RUNTIME_PATH)


def _load_runtime_from_file() -> dict | None:
    if not _RUNTIME_PATH.exists():
        return None
    try:
        data = json.loads(_RUNTIME_PATH.read_text(encoding="utf-8"))
        base = _build_runtime_from_env()
        if "provider" in data:
            base["provider"] = data["provider"]
        for key in ("local", "openai"):
            if key in data:
                for field in ("base_url", "model", "api_key"):
                    if field in data[key]:
                        base[key][field] = data[key][field]
        return base
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _runtime() -> dict:
    global _cached_runtime, _cached_at
    now = time.monotonic()
    if _cached_runtime is not None and (now - _cached_at) < _RUNTIME_CACHE_TTL:
        return _cached_runtime
    loaded = _load_runtime_from_file()
    if loaded is not None:
        _cached_runtime = loaded
    elif _cached_runtime is None:
        _cached_runtime = _build_runtime_from_env()
    _cached_at = now
    return _cached_runtime


def get_llm_runtime() -> dict:
    runtime = _runtime()
    provider: LlmProvider = runtime["provider"]
    active = runtime[provider]
    return {
        "provider": provider,
        "system": "openai_api" if provider == "openai" else "local_server",
        "model": active["model"],
        "base_url": active["base_url"],
        "available_models": {
            "local": [runtime["local"]["model"]],
            "openai": _supported_openai_models(),
        },
    }


def set_llm_runtime(provider: LlmProvider, model: str, openai_api_key: str | None = None) -> dict:
    global _cached_runtime, _cached_at
    runtime = _runtime().copy()
    runtime["local"] = runtime["local"].copy()
    runtime["openai"] = runtime["openai"].copy()
    if provider not in ("local", "openai"):
        raise ValueError("provider musi być 'local' albo 'openai'")
    if not model.strip():
        raise ValueError("model nie może być pusty")
    if provider == "openai" and model not in _supported_openai_models():
        raise ValueError(f"Niewspierany model OpenAI: {model}. Dostępne: {_supported_openai_models()}")

    runtime["provider"] = provider
    runtime[provider]["model"] = model.strip()
    if provider == "openai" and openai_api_key is not None:
        runtime["openai"]["api_key"] = openai_api_key.strip()

    _save_runtime(runtime)
    _cached_runtime = runtime
    _cached_at = time.monotonic()
    return get_llm_runtime()


def get_llm_client() -> AsyncOpenAI:
    runtime = _runtime()
    provider: LlmProvider = runtime["provider"]
    selected = runtime[provider]
    return AsyncOpenAI(
        base_url=selected["base_url"],
        api_key=selected["api_key"] or "no-key",
    )


def get_model_name() -> str:
    runtime = _runtime()
    provider: LlmProvider = runtime["provider"]
    return runtime[provider]["model"]


def _is_reasoning_model() -> bool:
    """Check if current OpenAI model uses reasoning tokens (gpt-5*, o1*, o3*)."""
    runtime = _runtime()
    if runtime["provider"] != "openai":
        return False
    model = runtime["openai"]["model"].lower()
    return any(model.startswith(p) for p in ("gpt-5", "o1", "o3"))


def max_tokens_param(limit: int) -> dict:
    """Return the correct max tokens parameter for current LLM provider.
    
    OpenAI newer models (gpt-4.1+, gpt-5*) require 'max_completion_tokens',
    while local servers and older models use 'max_tokens'.
    
    For reasoning models (gpt-5*, o1*, o3*), we add extra buffer for reasoning tokens.
    """
    runtime = _runtime()
    if runtime["provider"] == "openai":
        if _is_reasoning_model():
            return {"max_completion_tokens": limit + 8000}
        return {"max_completion_tokens": limit}
    return {"max_tokens": limit}


def temperature_param(temp: float) -> dict:
    """Return temperature parameter, but skip for OpenAI models that don't support it.
    
    Some OpenAI models (like gpt-5-mini) only support temperature=1.
    For safety, we skip the parameter for OpenAI and let it use the default.
    Local models support any temperature value.
    """
    runtime = _runtime()
    if runtime["provider"] == "openai":
        return {}
    return {"temperature": temp}
