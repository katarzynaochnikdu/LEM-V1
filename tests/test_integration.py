"""
Testy integracyjne - pełny pipeline end-to-end
"""

import pytest
from pathlib import Path
from app.modules.parser import ResponseParser
from app.modules.mapper import ResponseMapper
from app.modules.scorer import CompetencyScorer
from app.modules.feedback import FeedbackGenerator


@pytest.fixture
def pipeline():
    """Fixture z pełnym pipeline'em"""
    return {
        "parser": ResponseParser(),
        "mapper": ResponseMapper(),
        "scorer": CompetencyScorer(),
        "feedback": FeedbackGenerator()
    }


def get_sample_responses():
    """Zwraca listę wszystkich przykładowych odpowiedzi"""
    samples_dir = Path(__file__).parent / "sample_responses"
    return list(samples_dir.glob("response_level_*.txt"))


@pytest.mark.asyncio
@pytest.mark.parametrize("response_file", get_sample_responses())
async def test_full_pipeline(pipeline, response_file):
    """Test pełnego pipeline'u dla wszystkich przykładowych odpowiedzi"""
    # Wczytaj odpowiedź
    with open(response_file, "r", encoding="utf-8") as f:
        response_text = f.read()
    
    # MODUŁ 1: Parse
    parsed = await pipeline["parser"].parse(response_text)
    assert parsed.raw_text == response_text
    
    # MODUŁ 2: Map
    mapped = await pipeline["mapper"].map(parsed)
    assert len(mapped.evidence) == 7
    
    # MODUŁ 3: Score
    scoring_result = await pipeline["scorer"].score(mapped)
    assert 0.0 <= scoring_result.ocena_delegowanie <= 4.0
    
    # MODUŁ 4: Feedback
    feedback = await pipeline["feedback"].generate(scoring_result)
    assert feedback.summary
    assert feedback.recommendation
    assert len(feedback.mocne_strony) > 0 or len(feedback.obszary_rozwoju) > 0
    
    # Sprawdź jakość feedbacku
    quality = pipeline["feedback"].get_feedback_quality_score(feedback)
    print(f"\n{response_file.name}:")
    print(f"  Ocena: {scoring_result.ocena_delegowanie}/4.0")
    print(f"  Poziom: {scoring_result.poziom}")
    print(f"  Jakość feedbacku: {quality}")


@pytest.mark.asyncio
async def test_pipeline_consistency(pipeline):
    """Test czy ten sam input daje spójne wyniki"""
    # Wczytaj odpowiedź
    path = Path(__file__).parent / "sample_responses" / "response_level_2_efektywny.txt"
    with open(path, "r", encoding="utf-8") as f:
        response_text = f.read()
    
    # Uruchom pipeline 2 razy
    results = []
    for _ in range(2):
        parsed = await pipeline["parser"].parse(response_text)
        mapped = await pipeline["mapper"].map(parsed)
        scoring_result = await pipeline["scorer"].score(mapped)
        results.append(scoring_result.ocena_delegowanie)
    
    # Wyniki powinny być bardzo podobne (różnica max 0.5 punktu)
    assert abs(results[0] - results[1]) <= 0.5, \
        f"Wyniki niespójne: {results[0]} vs {results[1]}"


@pytest.mark.asyncio
async def test_expected_score_ranges(pipeline):
    """Test czy odpowiedzi dostają oczekiwane zakresy ocen"""
    test_cases = [
        ("response_level_0_nieefektywny.txt", 0.0, 1.5),
        ("response_level_1_bazowy.txt", 1.0, 2.25),
        ("response_level_2_efektywny.txt", 2.0, 3.0),
        ("response_level_3_biegly.txt", 3.0, 4.0)
    ]
    
    for filename, min_score, max_score in test_cases:
        path = Path(__file__).parent / "sample_responses" / filename
        with open(path, "r", encoding="utf-8") as f:
            response_text = f.read()
        
        parsed = await pipeline["parser"].parse(response_text)
        mapped = await pipeline["mapper"].map(parsed)
        scoring_result = await pipeline["scorer"].score(mapped)
        
        score = scoring_result.ocena_delegowanie
        print(f"\n{filename}: {score}/4.0 (oczekiwano: {min_score}-{max_score})")
        
        # Sprawdź czy wynik jest w oczekiwanym zakresie (z pewną tolerancją)
        assert min_score - 0.5 <= score <= max_score + 0.5, \
            f"{filename}: Wynik {score} poza oczekiwanym zakresem {min_score}-{max_score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
