"""
Moduł 2: Mapper - Mapowanie na wymiary kompetencji
Ekstrakcja cytatów-dowodów dla wymiarów (dynamicznie per kompetencja)
"""

import json
import os
from pathlib import Path
from app.llm_client import get_llm_client, get_model_name, max_tokens_param, temperature_param
from app.json_utils import extract_json_from_text
from app.models import ParsedResponse, MappedResponse, WymiarEvidence
from app.rubric import get_wymiary_for_competency
from app.prompt_manager import get_active_prompt_content


class ResponseMapper:
    """Mapper odpowiedzi na wymiary kompetencji z ekstrakcją dowodów"""

    def __init__(self, competency: str = "delegowanie"):
        self.competency = competency
        self.client = get_llm_client()
        self.model = get_model_name()
        self.prompt_template = get_active_prompt_content("map", competency)
        self.wymiary = get_wymiary_for_competency(competency)

    async def map(self, parsed_response: ParsedResponse) -> MappedResponse:
        """Mapuje sparsowaną odpowiedź na wymiary kompetencji."""
        sections_text = "\n\n".join(
            f"{key.upper().replace('_', ' ')}:\n{val}"
            for key, val in parsed_response.sections.items()
            if val
        )

        prompt = self.prompt_template.format(parsed_response=sections_text)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Jesteś ekspertem w ocenie kompetencji menedżerskich. Zwracasz wyłącznie poprawny JSON z ekstrakcją cytatów."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **temperature_param(0.1),
                **max_tokens_param(3000)
            )

            result_text = response.choices[0].message.content
            result_json = extract_json_from_text(result_text)

            evidence_dict = {}
            for wymiar_key in self.wymiary.keys():
                wymiar_data = result_json.get(wymiar_key, {})
                evidence_dict[wymiar_key] = WymiarEvidence(
                    wymiar=wymiar_key,
                    znalezione_fragmenty=wymiar_data.get("znalezione_fragmenty", [])[:2],
                    czy_obecny=wymiar_data.get("czy_obecny", False),
                    notatki=wymiar_data.get("notatki", "")
                )

            mapped = MappedResponse(
                evidence=evidence_dict,
                parsed_response=parsed_response
            )

            return mapped

        except json.JSONDecodeError as e:
            raise ValueError(f"Nie udało się sparsować JSON z odpowiedzi LLM: {e}")
        except Exception as e:
            raise ValueError(f"Błąd podczas mapowania odpowiedzi: {e}")

    def get_evidence_summary(self, mapped: MappedResponse) -> dict:
        """Zwraca podsumowanie znalezionych dowodów."""
        summary = {}
        for wymiar_key, evidence in mapped.evidence.items():
            summary[wymiar_key] = {
                "obecny": evidence.czy_obecny,
                "liczba_cytatow": len(evidence.znalezione_fragmenty),
                "notatki": evidence.notatki
            }
        return summary

    def count_present_dimensions(self, mapped: MappedResponse) -> int:
        """Zlicza ile wymiarów jest obecnych w odpowiedzi."""
        return sum(1 for evidence in mapped.evidence.values() if evidence.czy_obecny)
