"""
Moduł 4: Generator feedbacku
Generuje spersonalizowany, zróżnicowany feedback rozwojowy (dynamicznie per kompetencja)
"""

import json
from typing import Any
from app.llm_client import get_llm_client, get_model_name, max_tokens_param, temperature_param
from app.json_utils import extract_json_from_text
from app.models import ScoringResult, Feedback
from app.rubric import get_wymiary_for_competency
from app.prompt_manager import get_active_prompt_content, get_system_prompt


class FeedbackGenerator:
    """Generator spersonalizowanego feedbacku rozwojowego"""

    def __init__(self, competency: str = "delegowanie"):
        self.competency = competency
        self.client = get_llm_client()
        self.model = get_model_name()
        self.prompt_template = get_active_prompt_content("feedback", competency)
        self.system_prompt = get_system_prompt("feedback")
        self.wymiary = get_wymiary_for_competency(competency)
        self.last_usage: dict[str, Any] | None = None

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

    async def generate(self, scoring_result: ScoringResult) -> Feedback:
        """Generuje spersonalizowany feedback na podstawie wyniku scoringu."""
        dimension_scores_text = self._format_dimension_scores(scoring_result)
        evidence_text = self._format_evidence(scoring_result)

        prompt = self.prompt_template.format(
            score=scoring_result.ocena,
            level=scoring_result.poziom,
            dimension_scores=dimension_scores_text,
            evidence=evidence_text
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                **temperature_param(0.7),
                **max_tokens_param(3000)
            )

            self.last_usage = self._usage_to_dict(getattr(response, "usage", None))
            result_text = response.choices[0].message.content
            result_json = extract_json_from_text(result_text)

            feedback = Feedback(
                summary=result_json.get("summary", ""),
                recommendation=result_json.get("recommendation", ""),
                mocne_strony=result_json.get("mocne_strony", []),
                obszary_rozwoju=result_json.get("obszary_rozwoju", [])
            )

            return feedback

        except json.JSONDecodeError as e:
            raise ValueError(f"Nie udało się sparsować JSON z odpowiedzi LLM: {e}")
        except Exception as e:
            raise ValueError(f"Błąd podczas generowania feedbacku: {e}")

    def _format_dimension_scores(self, scoring_result: ScoringResult) -> str:
        """Formatuje oceny wymiarów do promptu."""
        lines = []
        for wymiar_key, dim_score in scoring_result.dimension_scores.items():
            wymiar_nazwa = self.wymiary[wymiar_key]['nazwa']
            lines.append(
                f"- {wymiar_nazwa}: {dim_score.ocena:.2f}/1.0 "
                f"(waga: {dim_score.waga:.0%}, punkty: {dim_score.punkty:.3f})"
            )
        return "\n".join(lines)

    def _format_evidence(self, scoring_result: ScoringResult) -> str:
        """Formatuje dowody (cytaty) do promptu."""
        lines = []
        for wymiar_key, evidence in scoring_result.mapped_response.evidence.items():
            wymiar_nazwa = self.wymiary[wymiar_key]['nazwa']

            if evidence.czy_obecny and evidence.znalezione_fragmenty:
                lines.append(f"\n{wymiar_nazwa}:")
                for i, fragment in enumerate(evidence.znalezione_fragmenty, 1):
                    lines.append(f"  {i}. \"{fragment}\"")
                if evidence.notatki:
                    lines.append(f"  Notatka: {evidence.notatki}")
            else:
                lines.append(f"\n{wymiar_nazwa}: BRAK DOWODÓW")

        return "\n".join(lines)

    def get_feedback_quality_score(self, feedback: Feedback) -> dict:
        """Ocenia jakość wygenerowanego feedbacku."""
        return {
            "summary_length": len(feedback.summary.split()),
            "recommendation_length": len(feedback.recommendation.split()),
            "num_strengths": len(feedback.mocne_strony),
            "num_development_areas": len(feedback.obszary_rozwoju),
            "is_valid": (
                50 <= len(feedback.summary.split()) <= 150 and
                10 <= len(feedback.recommendation.split()) <= 50 and
                len(feedback.mocne_strony) >= 1 and
                len(feedback.obszary_rozwoju) >= 1
            )
        }
