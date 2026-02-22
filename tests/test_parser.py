"""
Testy jednostkowe dla modułu Parser
"""

import pytest
from pathlib import Path
from app.modules.parser import ResponseParser


@pytest.fixture
def parser():
    """Fixture z parserem (wymaga OPENAI_API_KEY w env)"""
    return ResponseParser()


@pytest.fixture
def sample_response_efektywny():
    """Fixture z przykładową odpowiedzią poziomu efektywnego"""
    path = Path(__file__).parent / "sample_responses" / "response_level_2_efektywny.txt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.asyncio
async def test_parser_basic(parser, sample_response_efektywny):
    """Test podstawowego parsowania odpowiedzi"""
    parsed = await parser.parse(sample_response_efektywny)
    
    # Sprawdź czy wszystkie sekcje są wypełnione
    assert parsed.przygotowanie, "Sekcja 'przygotowanie' jest pusta"
    assert parsed.przebieg, "Sekcja 'przebieg' jest pusta"
    assert parsed.decyzje, "Sekcja 'decyzje' jest pusta"
    assert parsed.efekty, "Sekcja 'efekty' jest pusta"
    assert parsed.raw_text == sample_response_efektywny


@pytest.mark.asyncio
async def test_parser_validation(parser, sample_response_efektywny):
    """Test walidacji sparsowanej odpowiedzi"""
    parsed = await parser.parse(sample_response_efektywny)
    is_valid, missing = parser.validate_parsed_response(parsed)
    
    assert is_valid, f"Odpowiedź powinna być poprawna, brakuje: {missing}"
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_parser_short_response(parser):
    """Test parsowania zbyt krótkiej odpowiedzi"""
    short_response = "To jest bardzo krótka odpowiedź która nie spełnia wymagań."
    
    parsed = await parser.parse(short_response)
    is_valid, missing = parser.validate_parsed_response(parsed)
    
    assert not is_valid, "Krótka odpowiedź powinna być oznaczona jako niepoprawna"
    assert len(missing) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
