"""
Skrypt do uruchamiania kalibracji systemu
Uruchom: python calibration/run_calibration.py --input calibration_data/ --output calibration_results.json
"""

import asyncio
import json
from pathlib import Path
import sys
import os

# Dodaj główny katalog do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.parser import ResponseParser
from app.modules.mapper import ResponseMapper
from app.modules.scorer import CompetencyScorer


async def assess_response(response_text: str, response_id: str):
    """Ocenia pojedynczą odpowiedź"""
    parser = ResponseParser()
    mapper = ResponseMapper()
    scorer = CompetencyScorer()
    
    try:
        parsed = await parser.parse(response_text)
        mapped = await mapper.map(parsed)
        scoring_result = await scorer.score(mapped)
        
        return {
            "response_id": response_id,
            "score": scoring_result.ocena_delegowanie,
            "level": scoring_result.poziom,
            "dimension_scores": {
                k: v.ocena for k, v in scoring_result.dimension_scores.items()
            },
            "status": "success"
        }
    except Exception as e:
        return {
            "response_id": response_id,
            "status": "error",
            "error": str(e)
        }


async def run_calibration(input_dir: Path, output_file: Path):
    """Uruchamia kalibrację na wszystkich plikach w katalogu"""
    if not input_dir.exists():
        print(f"BŁĄD: Katalog {input_dir} nie istnieje")
        return
    
    response_files = list(input_dir.glob("*.txt"))
    if not response_files:
        print(f"BŁĄD: Brak plików .txt w katalogu {input_dir}")
        return
    
    print(f"Znaleziono {len(response_files)} plików do przetworzenia")
    results = []
    
    for i, response_file in enumerate(sorted(response_files), 1):
        print(f"[{i}/{len(response_files)}] Przetwarzanie: {response_file.name}")
        
        with open(response_file, "r", encoding="utf-8") as f:
            response_text = f.read()
        
        result = await assess_response(response_text, response_file.stem)
        results.append(result)
        
        if result["status"] == "success":
            print(f"  ✓ Ocena: {result['score']}/4.0 ({result['level']})")
        else:
            print(f"  ✗ Błąd: {result['error']}")
    
    # Zapisz wyniki
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Wyniki zapisane do: {output_file}")
    print(f"Przetworzono: {len(results)} odpowiedzi")
    successful = sum(1 for r in results if r["status"] == "success")
    print(f"Sukces: {successful}/{len(results)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Sprawdź API key
    if not os.getenv("OPENAI_API_KEY"):
        print("BŁĄD: Brak OPENAI_API_KEY w zmiennych środowiskowych")
        print("Utwórz plik .env i dodaj: OPENAI_API_KEY=your_key_here")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="Uruchom kalibrację systemu oceny LEM")
    parser.add_argument("--input", required=True, help="Katalog z odpowiedziami (.txt)")
    parser.add_argument("--output", required=True, help="Plik wyjściowy JSON")
    args = parser.parse_args()
    
    asyncio.run(run_calibration(
        Path(args.input),
        Path(args.output)
    ))
