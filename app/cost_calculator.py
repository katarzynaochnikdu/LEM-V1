"""
Kalkulator kosztów dla modeli OpenAI na podstawie config/pricing.json.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PRICING_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "pricing.json"


@lru_cache(maxsize=1)
def _load_pricing_config() -> dict[str, Any]:
    with open(PRICING_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_model_key(model: str) -> str:
    normalized = model.strip().lower()
    models = _load_pricing_config().get("models", {})

    if normalized in models:
        return normalized

    for key in models.keys():
        if normalized.startswith(f"{key}-"):
            return key

    raise ValueError(f"Brak cennika dla modelu: {model}")


def get_model_pricing(model: str) -> dict[str, Any]:
    model_key = _resolve_model_key(model)
    pricing = _load_pricing_config()["models"][model_key]
    return {
        "requested_model": model,
        "model": model_key,
        "input_per_1m": float(pricing["input_per_1m"]),
        "cached_input_per_1m": float(pricing["cached_input_per_1m"]),
        "output_per_1m": float(pricing["output_per_1m"]),
        "is_reasoning": bool(pricing.get("is_reasoning", False)),
    }


def list_model_pricing() -> dict[str, dict[str, Any]]:
    models = _load_pricing_config().get("models", {})
    return {
        key: {
            "input_per_1m": float(value["input_per_1m"]),
            "cached_input_per_1m": float(value["cached_input_per_1m"]),
            "output_per_1m": float(value["output_per_1m"]),
            "is_reasoning": bool(value.get("is_reasoning", False)),
        }
        for key, value in models.items()
    }


def get_estimated_tokens_per_evaluation() -> dict[str, int]:
    estimated = _load_pricing_config().get("estimated_tokens_per_evaluation", {})
    return {
        "input": int(estimated.get("input", 10000)),
        "output": int(estimated.get("output", 8100)),
    }


def calculate_cost_breakdown(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> dict[str, Any]:
    if input_tokens < 0 or output_tokens < 0 or cached_input_tokens < 0:
        raise ValueError("Liczba tokenów nie może być ujemna")
    if cached_input_tokens > input_tokens:
        raise ValueError("cached_input_tokens nie może być większe niż input_tokens")

    pricing = get_model_pricing(model)
    uncached_input_tokens = input_tokens - cached_input_tokens

    input_cost = (uncached_input_tokens / 1_000_000) * pricing["input_per_1m"]
    cached_input_cost = (cached_input_tokens / 1_000_000) * pricing["cached_input_per_1m"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
    total_cost = input_cost + cached_input_cost + output_cost

    return {
        "model": pricing["model"],
        "requested_model": pricing["requested_model"],
        "tokens": {
            "input": input_tokens,
            "cached_input": cached_input_tokens,
            "uncached_input": uncached_input_tokens,
            "output": output_tokens,
        },
        "rates_per_1m": {
            "input": pricing["input_per_1m"],
            "cached_input": pricing["cached_input_per_1m"],
            "output": pricing["output_per_1m"],
        },
        "cost_usd": {
            "input": round(input_cost, 6),
            "cached_input": round(cached_input_cost, 6),
            "output": round(output_cost, 6),
            "total": round(total_cost, 6),
        },
        "is_reasoning": pricing["is_reasoning"],
    }


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    breakdown = calculate_cost_breakdown(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
    )
    return float(breakdown["cost_usd"]["total"])


def estimate_evaluation_cost(
    model: str,
    count: int = 1,
    cached_input_ratio: float = 0.0,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> dict[str, Any]:
    if count < 1:
        raise ValueError("count musi być >= 1")
    if not (0.0 <= cached_input_ratio <= 1.0):
        raise ValueError("cached_input_ratio musi być w zakresie 0.0 - 1.0")

    estimated = get_estimated_tokens_per_evaluation()
    input_per_eval = input_tokens if input_tokens is not None else estimated["input"]
    output_per_eval = output_tokens if output_tokens is not None else estimated["output"]
    cached_input_per_eval = int(round(input_per_eval * cached_input_ratio))

    per_evaluation = calculate_cost_breakdown(
        model=model,
        input_tokens=input_per_eval,
        output_tokens=output_per_eval,
        cached_input_tokens=cached_input_per_eval,
    )
    total_cost = round(per_evaluation["cost_usd"]["total"] * count, 6)

    return {
        "model": per_evaluation["model"],
        "requested_model": per_evaluation["requested_model"],
        "count": count,
        "cached_input_ratio": cached_input_ratio,
        "per_evaluation": per_evaluation,
        "total_cost_usd": total_cost,
    }
