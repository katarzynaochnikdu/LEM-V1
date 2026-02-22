"""
Centralny klient LLM - kompatybilny z vLLM/OpenAI API
Konfigurowany przez zmienne środowiskowe
"""

import os
from openai import AsyncOpenAI


def get_llm_client() -> AsyncOpenAI:
    """
    Tworzy klienta LLM kompatybilnego z OpenAI API.
    Obsługuje zarówno OpenAI, jak i lokalne serwery vLLM.
    
    Zmienne środowiskowe:
        OPENAI_API_KEY: Klucz API
        OPENAI_BASE_URL: URL serwera (domyślnie: http://localhost:8000/v1 dla vLLM)
        OPENAI_MODEL: Nazwa modelu
    """
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:8000/v1")
    api_key = os.getenv("OPENAI_API_KEY", "no-key")
    
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )


def get_model_name() -> str:
    """Zwraca nazwę modelu do użycia"""
    return os.getenv("OPENAI_MODEL", "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ")
