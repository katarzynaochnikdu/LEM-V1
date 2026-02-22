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


_llm_runtime: dict | None = None


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


def _runtime() -> dict:
    global _llm_runtime
    if _llm_runtime is None:
        _llm_runtime = _build_runtime_from_env()
    return _llm_runtime


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
    runtime = _runtime()
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
