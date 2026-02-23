"""
Moduł 3: Scorer - Algorytm oceny kompetencji
Przypisuje ocenę 0-4 (co 0.25) na podstawie analizy wymiarów (dynamicznie per kompetencja)
"""

import json
import re
from pathlib import Path
from typing import Any
from app.llm_client import get_llm_client, get_model_name, max_tokens_param, temperature_param
from app.models import MappedResponse, ScoringResult, DimensionScore
from app.rubric import get_wymiary_for_competency, get_poziom_kompetencji
from app.prompt_manager import get_active_prompt_content, get_system_prompt


class CompetencyScorer:
    """Scorer oceniający kompetencję na podstawie wymiarów"""

    def __init__(self, competency: str = "delegowanie", weights_path: str = None):
        self.competency = competency
        self.client = get_llm_client()
        self.model = get_model_name()
        self.wymiary = get_wymiary_for_competency(competency)

        if weights_path is None:
            weights_path = Path(__file__).parent.parent.parent / "config" / "weights.json"

        with open(weights_path, "r", encoding="utf-8") as f:
            weights_data = json.load(f)
            self.weights = weights_data[competency]

        self.prompt_template = get_active_prompt_content("score", competency)
        self.system_prompt = get_system_prompt("score")
        self.last_usage: dict[str, Any] | None = None
        self._accumulated_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _usage_to_dict(self, usage: Any) -> dict[str, Any]:
        if usage is None:
            return {}
        if isinstance(usage, dict):
            return usage
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        if hasattr(usage, "__dict__"):
            return dict(usage.__dict__)
        return {}

    def _accumulate_usage(self, usage: Any) -> None:
        d = self._usage_to_dict(usage)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            self._accumulated_usage[key] += int(d.get(key, 0))

    async def score(self, mapped_response: MappedResponse) -> ScoringResult:
        """Ocenia kompetencję na podstawie zmapowanej odpowiedzi."""
        self._accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        dimension_scores = {}
        total_weighted_score = 0.0

        for wymiar_key, evidence in mapped_response.evidence.items():
            wymiar_score = await self._score_dimension(wymiar_key, evidence, mapped_response)
            waga = self.weights.get(wymiar_key, 0.0)
            punkty = wymiar_score * waga
            total_weighted_score += punkty

            dimension_scores[wymiar_key] = DimensionScore(
                wymiar=wymiar_key,
                ocena=wymiar_score,
                waga=waga,
                punkty=punkty,
                uzasadnienie=self._get_dimension_justification(wymiar_key, wymiar_score, evidence)
            )

        final_score = total_weighted_score * 4.0
        final_score = round(final_score * 4) / 4
        final_score = max(0.0, min(4.0, final_score))

        poziom = get_poziom_kompetencji(final_score)

        self.last_usage = dict(self._accumulated_usage)
        return ScoringResult(
            ocena=final_score,
            poziom=poziom.value,
            dimension_scores=dimension_scores,
            mapped_response=mapped_response
        )

    async def _score_dimension(
        self,
        wymiar_key: str,
        evidence,
        mapped_response: MappedResponse
    ) -> float:
        """Ocenia pojedynczy wymiar w skali 0-1."""
        if not evidence.czy_obecny or len(evidence.znalezione_fragmenty) == 0:
            return 0.0

        wymiar_def = self.wymiary[wymiar_key]

        prompt = self.prompt_template.format(
            wymiar_nazwa=wymiar_def['nazwa'],
            wymiar_opis=wymiar_def['opis'],
            poziomy=self._format_levels(wymiar_def['poziomy']),
            dowody=self._format_evidence(evidence),
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                **temperature_param(0.1),
                **max_tokens_param(10)
            )

            self._accumulate_usage(getattr(response, "usage", None))
            score_text = response.choices[0].message.content.strip()
            match = re.search(r'(\d+\.?\d*)', score_text)
            if match:
                score = float(match.group(1))
            else:
                return self._fallback_score(evidence)

            score = max(0.0, min(1.0, score))
            return score

        except Exception:
            return self._fallback_score(evidence)

    def _fallback_score(self, evidence) -> float:
        """Prosta heurystyka scoringu w przypadku błędu LLM."""
        if not evidence.czy_obecny:
            return 0.0
        num_citations = len(evidence.znalezione_fragmenty)
        if num_citations == 0:
            return 0.0
        elif num_citations == 1:
            return 0.5
        else:
            return 0.7

    def _format_levels(self, poziomy: dict) -> str:
        """Formatuje poziomy wymiaru do promptu."""
        lines = []
        for level, data in sorted(poziomy.items()):
            lines.append(f"Poziom {level}: {data['opis']}")
        return "\n".join(lines)

    def _format_evidence(self, evidence) -> str:
        """Formatuje dowody do promptu."""
        if not evidence.znalezione_fragmenty:
            return "BRAK DOWODÓW"

        lines = []
        for i, fragment in enumerate(evidence.znalezione_fragmenty, 1):
            lines.append(f"Cytat {i}: \"{fragment}\"")

        if evidence.notatki:
            lines.append(f"\nNotatka: {evidence.notatki}")

        return "\n".join(lines)

    def _get_dimension_justification(self, wymiar_key: str, score: float, evidence) -> str:
        """Generuje krótkie uzasadnienie oceny wymiaru."""
        wymiar_nazwa = self.wymiary[wymiar_key]['nazwa']

        if score == 0.0:
            return f"Brak dowodów realizacji: {wymiar_nazwa}"
        elif score < 0.4:
            return f"Minimalna realizacja: {wymiar_nazwa} - {evidence.notatki or 'ogólnikowe podejście'}"
        elif score < 0.7:
            return f"Podstawowa realizacja: {wymiar_nazwa} - {evidence.notatki or 'obecne elementy kluczowe'}"
        elif score < 0.9:
            return f"Dobra realizacja: {wymiar_nazwa} - {evidence.notatki or 'konkretne dowody'}"
        else:
            return f"Doskonała realizacja: {wymiar_nazwa} - {evidence.notatki or 'pełna realizacja wymiaru'}"
