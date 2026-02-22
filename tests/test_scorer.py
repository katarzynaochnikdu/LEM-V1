"""
Testy jednostkowe dla modułu Scorer
"""

import pytest
from pathlib import Path
from app.modules.parser import ResponseParser
from app.modules.mapper import ResponseMapper
from app.modules.scorer import CompetencyScorer


@pytest.fixture
def scorer():
    """Fixture z scorerem"""
    return CompetencyScorer()


@pytest.fixture
def parser():
    """Fixture z parserem"""
    return ResponseParser()


@pytest.fixture
def mapper():
    """Fixture z mapperem"""
    return ResponseMapper()


@pytest.mark.asyncio
async def test_scorer_basic(parser, mapper, scorer):
    """Test podstawowego scoringu"""
    # Wczytaj przykładową odpowiedź
    path = Path(__file__).parent / "sample_responses" / "response_level_2_efektywny.txt"
    with open(path, "r", encoding="utf-8") as f:
        response_text = f.read()
    
    # Przetwórz przez pipeline
    parsed = await parser.parse(response_text)
    mapped = await mapper.map(parsed)
    scoring_result = await scorer.score(mapped)
    
    # Sprawdź wynik
    assert 0.0 <= scoring_result.ocena_delegowanie <= 4.0
    assert scoring_result.poziom in [
        "Nieefektywny (Nieświadoma niekompetencja)",
        "Bazowy (Świadoma niekompetencja)",
        "Efektywny (Świadoma kompetencja)",
        "Biegły (Nieświadoma kompetencja)"
    ]
    assert len(scoring_result.dimension_scores) == 7


@pytest.mark.asyncio
async def test_scorer_dimension_scores(parser, mapper, scorer):
    """Test czy wszystkie wymiary są ocenione"""
    path = Path(__file__).parent / "sample_responses" / "response_level_2_efektywny.txt"
    with open(path, "r", encoding="utf-8") as f:
        response_text = f.read()
    
    parsed = await parser.parse(response_text)
    mapped = await mapper.map(parsed)
    scoring_result = await scorer.score(mapped)
    
    # Sprawdź czy wszystkie wymiary mają oceny
    expected_dimensions = [
        "intencja", "stan_docelowy", "metoda_pomiaru",
        "poziom_odpowiedzialnosci", "harmonogram",
        "monitorowanie", "sprawdzenie_zrozumienia"
    ]
    
    for dim in expected_dimensions:
        assert dim in scoring_result.dimension_scores
        dim_score = scoring_result.dimension_scores[dim]
        assert 0.0 <= dim_score.ocena <= 1.0
        assert 0.0 <= dim_score.waga <= 1.0
        assert dim_score.uzasadnienie


@pytest.mark.asyncio
async def test_scorer_score_range(parser, mapper, scorer):
    """Test czy wynik jest w poprawnym zakresie i zaokrąglony do 0.25"""
    path = Path(__file__).parent / "sample_responses" / "response_level_3_biegly.txt"
    with open(path, "r", encoding="utf-8") as f:
        response_text = f.read()
    
    parsed = await parser.parse(response_text)
    mapped = await mapper.map(parsed)
    scoring_result = await scorer.score(mapped)
    
    # Sprawdź zakres
    assert 0.0 <= scoring_result.ocena_delegowanie <= 4.0
    
    # Sprawdź zaokrąglenie do 0.25
    score = scoring_result.ocena_delegowanie
    assert score * 4 == int(score * 4), f"Wynik {score} nie jest zaokrąglony do 0.25"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
