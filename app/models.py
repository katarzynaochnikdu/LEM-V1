"""
Modele Pydantic dla systemu oceny LEM
Obsługuje 4 kompetencje: delegowanie, podejmowanie_decyzji, okreslanie_priorytetow, udzielanie_feedbacku
"""

from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Dict, List, Optional
from datetime import datetime


VALID_COMPETENCIES = [
    "delegowanie",
    "podejmowanie_decyzji",
    "okreslanie_priorytetow",
    "udzielanie_feedbacku",
]


class AssessmentRequest(BaseModel):
    """Request do API /assess"""
    participant_id: str = Field(..., description="ID uczestnika")
    response_text: str = Field(..., min_length=50, description="Odpowiedź uczestnika (min 50 znaków)")
    competency: str = Field(default="delegowanie", description="Oceniana kompetencja")
    case_id: str = Field(default="lem_v1", description="ID case'u")

    @field_validator('response_text')
    @classmethod
    def validate_response_length(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError('Odpowiedź musi mieć minimum 50 znaków')
        return v.strip()

    @field_validator('competency')
    @classmethod
    def validate_competency(cls, v: str) -> str:
        if v not in VALID_COMPETENCIES:
            raise ValueError(f'Nieznana kompetencja: {v}. Dostępne: {VALID_COMPETENCIES}')
        return v


class ParsedResponse(BaseModel):
    """Strukturyzowana odpowiedź po parsowaniu - generyczna (sekcje jako dict)"""
    sections: Dict[str, str] = Field(..., description="Sekcje odpowiedzi (klucz -> treść)")
    raw_text: str = Field(..., description="Oryginalny tekst odpowiedzi")

    @property
    def przygotowanie(self) -> str:
        return self.sections.get("przygotowanie", "")

    @property
    def przebieg(self) -> str:
        return self.sections.get("przebieg", "")

    @property
    def decyzje(self) -> str:
        return self.sections.get("decyzje", "")

    @property
    def efekty(self) -> str:
        return self.sections.get("efekty", "")


class WymiarEvidence(BaseModel):
    """Dowody dla pojedynczego wymiaru"""
    wymiar: str = Field(..., description="Nazwa wymiaru")
    znalezione_fragmenty: List[str] = Field(default_factory=list, description="Cytaty z odpowiedzi (max 2)")
    czy_obecny: bool = Field(..., description="Czy wymiar jest obecny w odpowiedzi")
    notatki: Optional[str] = Field(None, description="Dodatkowe notatki z analizy")


class MappedResponse(BaseModel):
    """Odpowiedź po mapowaniu na wymiary"""
    evidence: Dict[str, WymiarEvidence] = Field(..., description="Dowody dla każdego wymiaru")
    parsed_response: ParsedResponse = Field(..., description="Sparsowana odpowiedź")


class DimensionScore(BaseModel):
    """Ocena pojedynczego wymiaru"""
    wymiar: str = Field(..., description="Nazwa wymiaru")
    ocena: float = Field(..., ge=0.0, le=1.0, description="Ocena wymiaru w skali 0-1")
    waga: float = Field(..., ge=0.0, le=1.0, description="Waga wymiaru")
    punkty: float = Field(..., description="Punkty = ocena * waga")
    uzasadnienie: str = Field(..., description="Krótkie uzasadnienie oceny")


class ScoringResult(BaseModel):
    """Wynik scoringu"""
    ocena: float = Field(..., ge=0.0, le=4.0, description="Ocena końcowa 0-4")
    poziom: str = Field(..., description="Poziom kompetencji (Nieefektywny/Bazowy/Efektywny/Biegły)")
    dimension_scores: Dict[str, DimensionScore] = Field(..., description="Oceny poszczególnych wymiarów")
    mapped_response: MappedResponse = Field(..., description="Zmapowana odpowiedź z dowodami")

    @property
    def ocena_delegowanie(self) -> float:
        """Backward compatibility alias."""
        return self.ocena


class Feedback(BaseModel):
    """Wygenerowany feedback"""
    summary: str = Field(..., max_length=500, description="Uzasadnienie oceny (2-3 zdania)")
    recommendation: str = Field(..., max_length=200, description="Konkretna rekomendacja rozwojowa")
    mocne_strony: List[str] = Field(default_factory=list, description="Lista mocnych stron (z cytatami)")
    obszary_rozwoju: List[str] = Field(default_factory=list, description="Lista obszarów do rozwoju")


class AssessmentResponse(BaseModel):
    """Pełna odpowiedź API /assess"""
    participant_id: str = Field(..., description="ID uczestnika")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp oceny")
    competency: str = Field(default="delegowanie", description="Oceniana kompetencja")
    score: float = Field(..., ge=0.0, le=4.0, description="Ocena końcowa 0-4")
    level: str = Field(..., description="Poziom kompetencji")

    evidence: Dict[str, List[str]] = Field(..., description="Cytaty-dowody dla każdego wymiaru")
    feedback: Feedback = Field(..., description="Spersonalizowany feedback")
    dimension_scores: Dict[str, float] = Field(..., description="Oceny wymiarów (0-1)")

    scoring_details: Optional[ScoringResult] = Field(None, description="Szczegółowe dane scoringu (opcjonalne)")


class HealthResponse(BaseModel):
    """Response dla endpoint /health"""
    status: str = Field(default="healthy")
    version: str = Field(default="2.0.0")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
