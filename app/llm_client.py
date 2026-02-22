"""
Centralny klient LLM - przełączanie między local-server i OpenAI API.
"""

import os
from typing import Literal
from openai import AsyncOpenAI


LlmProvider = Literal["local", "openai"]


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


_llm_runtime = {
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


def get_llm_runtime() -> dict:
    provider: LlmProvider = _llm_runtime["provider"]
    active = _llm_runtime[provider]
    return {
        "provider": provider,
        "system": "openai_api" if provider == "openai" else "local_server",
        "model": active["model"],
        "base_url": active["base_url"],
        "available_models": {
            "local": [_llm_runtime["local"]["model"]],
            "openai": _supported_openai_models(),
        },
    }


def set_llm_runtime(provider: LlmProvider, model: str, openai_api_key: str | None = None) -> dict:
    if provider not in ("local", "openai"):
        raise ValueError("provider musi być 'local' albo 'openai'")
    if not model.strip():
        raise ValueError("model nie może być pusty")
    if provider == "openai" and model not in _supported_openai_models():
        raise ValueError(f"Niewspierany model OpenAI: {model}. Dostępne: {_supported_openai_models()}")

    _llm_runtime["provider"] = provider
    _llm_runtime[provider]["model"] = model.strip()
    if provider == "openai" and openai_api_key is not None:
        _llm_runtime["openai"]["api_key"] = openai_api_key.strip()
    return get_llm_runtime()


def get_llm_client() -> AsyncOpenAI:
    provider: LlmProvider = _llm_runtime["provider"]
    selected = _llm_runtime[provider]
    return AsyncOpenAI(
        base_url=selected["base_url"],
        api_key=selected["api_key"] or "no-key",
    )


def get_model_name() -> str:
    provider: LlmProvider = _llm_runtime["provider"]
    return _llm_runtime[provider]["model"]
