"""
Skrypt do manualnego testowania pełnego pipeline'u
Uruchom: python tests/run_manual_test.py
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

from app.modules.parser import ResponseParser
from app.modules.mapper import ResponseMapper
from app.modules.scorer import CompetencyScorer
from app.modules.feedback import FeedbackGenerator


async def test_single_response(response_file: Path):
    """Testuje pojedynczą odpowiedź przez cały pipeline"""
    print(f"\n{'='*80}")
    print(f"TESTOWANIE: {response_file.name}")
    print(f"{'='*80}\n")
    
    # Wczytaj odpowiedź
    with open(response_file, "r", encoding="utf-8") as f:
        response_text = f.read()
    
    print(f"Długość odpowiedzi: {len(response_text)} znaków\n")
    
    # Inicjalizuj moduły
    parser = ResponseParser()
    mapper = ResponseMapper()
    scorer = CompetencyScorer()
    feedback_gen = FeedbackGenerator()
    
    # MODUŁ 1: Parse
    print("MODUŁ 1: Parsowanie...")
    parsed = await parser.parse(response_text)
    print(f"✓ Sparsowano na 4 sekcje")
    print(f"  - Przygotowanie: {len(parsed.przygotowanie)} znaków")
    print(f"  - Przebieg: {len(parsed.przebieg)} znaków")
    print(f"  - Decyzje: {len(parsed.decyzje)} znaków")
    print(f"  - Efekty: {len(parsed.efekty)} znaków")
    
    # MODUŁ 2: Map
    print("\nMODUŁ 2: Mapowanie na wymiary...")
    mapped = await mapper.map(parsed)
    present_count = mapper.count_present_dimensions(mapped)
    print(f"✓ Znaleziono {present_count}/7 wymiarów")
    
    for wymiar_key, evidence in mapped.evidence.items():
        status = "✓" if evidence.czy_obecny else "✗"
        cytaty = len(evidence.znalezione_fragmenty)
        print(f"  {status} {wymiar_key}: {cytaty} cytatów - {evidence.notatki[:50]}...")
    
    # MODUŁ 3: Score
    print("\nMODUŁ 3: Scoring...")
    scoring_result = await scorer.score(mapped)
    print(f"✓ Ocena końcowa: {scoring_result.ocena_delegowanie}/4.0")
    print(f"  Poziom: {scoring_result.poziom}")
    print(f"\n  Breakdown wymiarów:")
    for wymiar_key, dim_score in scoring_result.dimension_scores.items():
        print(f"    - {wymiar_key}: {dim_score.ocena:.2f} (waga: {dim_score.waga:.0%}, punkty: {dim_score.punkty:.3f})")
    
    # MODUŁ 4: Feedback
    print("\nMODUŁ 4: Generowanie feedbacku...")
    feedback = await feedback_gen.generate(scoring_result)
    print(f"✓ Wygenerowano feedback")
    print(f"\n  PODSUMOWANIE:")
    print(f"  {feedback.summary}")
    print(f"\n  REKOMENDACJA:")
    print(f"  {feedback.recommendation}")
    print(f"\n  MOCNE STRONY ({len(feedback.mocne_strony)}):")
    for mocna in feedback.mocne_strony:
        print(f"    • {mocna}")
    print(f"\n  OBSZARY ROZWOJU ({len(feedback.obszary_rozwoju)}):")
    for rozwoj in feedback.obszary_rozwoju:
        print(f"    • {rozwoj}")
    
    # Jakość feedbacku
    quality = feedback_gen.get_feedback_quality_score(feedback)
    print(f"\n  Jakość feedbacku: {'✓ VALID' if quality['is_valid'] else '✗ INVALID'}")
    print(f"    - Długość podsumowania: {quality['summary_length']} słów")
    print(f"    - Długość rekomendacji: {quality['recommendation_length']} słów")


async def test_all_responses():
    """Testuje wszystkie przykładowe odpowiedzi"""
    samples_dir = Path(__file__).parent / "sample_responses"
    response_files = sorted(samples_dir.glob("response_level_*.txt"))
    
    print(f"\nZnaleziono {len(response_files)} przykładowych odpowiedzi")
    
    for response_file in response_files:
        await test_single_response(response_file)
    
    print(f"\n{'='*80}")
    print("WSZYSTKIE TESTY ZAKOŃCZONE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # Sprawdź czy jest API key
    if not os.getenv("OPENAI_API_KEY"):
        print("BŁĄD: Brak OPENAI_API_KEY w zmiennych środowiskowych")
        print("Utwórz plik .env i dodaj: OPENAI_API_KEY=your_key_here")
        exit(1)
    
    # Uruchom testy
    asyncio.run(test_all_responses())
