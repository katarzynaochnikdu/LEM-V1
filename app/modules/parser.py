"""
Moduł 1: Parser - Strukturyzacja odpowiedzi
Rozbija narracyjną odpowiedź na logiczne sekcje (dynamicznie per kompetencja)
"""

import json
import os
from pathlib import Path
from app.llm_client import get_llm_client, get_model_name
from app.json_utils import extract_json_from_text
from app.models import ParsedResponse
from app.prompt_manager import get_active_prompt_content

PARSE_SECTIONS = {
    "delegowanie": {
        "keys": ["przygotowanie", "przebieg", "decyzje", "efekty"],
        "labels": {
            "przygotowanie": "Przygotowanie do rozmowy",
            "przebieg": "Przebieg rozmowy krok po kroku",
            "decyzje": "Sposób podejmowania decyzji co i jak delegować",
            "efekty": "Planowane efekty rozmowy delegującej",
        },
    },
    "podejmowanie_decyzji": {
        "keys": ["kontekst_sytuacji", "analiza_kryteriow", "proces_decyzyjny", "komunikacja_wdrozenie"],
        "labels": {
            "kontekst_sytuacji": "Kontekst sytuacji i analiza otoczenia",
            "analiza_kryteriow": "Analiza kryteriów decyzyjnych i ryzyk",
            "proces_decyzyjny": "Proces podejmowania decyzji i scenariusze",
            "komunikacja_wdrozenie": "Komunikacja decyzji i plan wdrożenia",
        },
    },
    "okreslanie_priorytetow": {
        "keys": ["analiza_celow", "kontekst_priorytetow", "proces_priorytetyzacji", "kaskadowanie_komunikacja"],
        "labels": {
            "analiza_celow": "Analiza celów i priorytetów",
            "kontekst_priorytetow": "Kontekst i zmienne wpływające na priorytety",
            "proces_priorytetyzacji": "Proces priorytetyzacji i kryteria",
            "kaskadowanie_komunikacja": "Kaskadowanie i komunikacja priorytetów",
        },
    },
    "udzielanie_feedbacku": {
        "keys": ["opis_sytuacji", "przebieg_rozmowy", "reakcja_pracownika", "ustalenia_wnioski"],
        "labels": {
            "opis_sytuacji": "Opis sytuacji i zachowań pracownika",
            "przebieg_rozmowy": "Przebieg rozmowy feedbackowej",
            "reakcja_pracownika": "Reakcja pracownika i dialog",
            "ustalenia_wnioski": "Ustalenia, oczekiwania i wnioski",
        },
    },
}


def get_sections_for_competency(competency: str) -> dict:
    """Zwraca definicję sekcji parsowania dla danej kompetencji."""
    if competency not in PARSE_SECTIONS:
        raise ValueError(f"Nieznana kompetencja: {competency}")
    return PARSE_SECTIONS[competency]


class ResponseParser:
    """Parser odpowiedzi uczestnika na strukturyzowane sekcje"""

    def __init__(self, competency: str = "delegowanie"):
        self.competency = competency
        self.client = get_llm_client()
        self.model = get_model_name()
        self.prompt_template = get_active_prompt_content("parse", competency)
        self.sections_def = get_sections_for_competency(competency)

    async def parse(self, response_text: str) -> ParsedResponse:
        """Parsuje odpowiedź uczestnika na strukturyzowane sekcje."""
        prompt = self.prompt_template.format(response_text=response_text)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Jesteś ekspertem w analizie strukturalnej tekstów. Zwracasz wyłącznie poprawny JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )

            result_text = response.choices[0].message.content
            result_json = extract_json_from_text(result_text)

            sections = {}
            for key in self.sections_def["keys"]:
                sections[key] = result_json.get(key, "")

            parsed = ParsedResponse(
                sections=sections,
                raw_text=response_text
            )

            return parsed

        except json.JSONDecodeError as e:
            raise ValueError(f"Nie udało się sparsować JSON z odpowiedzi LLM: {e}")
        except Exception as e:
            raise ValueError(f"Błąd podczas parsowania odpowiedzi: {e}")

    def validate_parsed_response(self, parsed: ParsedResponse) -> tuple[bool, list[str]]:
        """Waliduje czy sparsowana odpowiedź ma wystarczającą zawartość."""
        missing = []
        for key in self.sections_def["keys"]:
            val = parsed.sections.get(key, "")
            if not val or len(val.strip()) < 20:
                missing.append(key)
        return len(missing) == 0, missing
