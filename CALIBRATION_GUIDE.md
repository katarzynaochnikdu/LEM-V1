# Instrukcja Kalibracji Systemu Oceny LEM

## Cel kalibracji

Kalibracja ma na celu **dostosowanie wag wymiarów** tak, aby oceny generowane przez system AI były zgodne z ocenami ekspertów-asesorów. Dobrze skalibrowany system powinien osiągnąć:

- **Korelację Pearsona > 0.85** między ocenami AI a ocenami asesorów
- **Mean Absolute Error < 0.5 punktu** (na skali 0-4)
- **Zgodność poziomów ±1 poziom** w minimum 85% przypadków

---

## Proces kalibracji - krok po kroku

### KROK 1: Zebranie danych referencyjnych (20-30 odpowiedzi)

**Cel**: Uzyskać zestaw odpowiedzi z ocenami ekspertów jako punkt odniesienia.

**Jak to zrobić**:

1. Zbierz 20-30 prawdziwych odpowiedzi uczestników assessmentu
2. Upewnij się że odpowiedzi reprezentują różne poziomy jakości:
   - 5-7 odpowiedzi poziomu Nieefektywny (0-1)
   - 5-7 odpowiedzi poziomu Bazowy (1-2)
   - 5-7 odpowiedzi poziomu Efektywny (2-3)
   - 5-7 odpowiedzi poziomu Biegły (3-4)

3. Zapisz każdą odpowiedź jako osobny plik tekstowy:
   ```
   calibration_data/
   ├── response_001.txt
   ├── response_002.txt
   └── ...
   ```

### KROK 2: Ocena przez asesorów

**Cel**: Uzyskać referencyjne oceny od 2-3 niezależnych asesorów.

**Jak to zrobić**:

1. Użyj template'u oceny (plik `calibration_template.xlsx` poniżej)
2. Każdy asesor ocenia **niezależnie** wszystkie 20-30 odpowiedzi
3. Asesorzy oceniają według tej samej rubryki co system AI (7 wymiarów)
4. Dla każdej odpowiedzi asesor podaje:
   - Ocenę końcową (0-4, co 0.25)
   - Ocenę każdego z 7 wymiarów (0-1)
   - Krótkie uzasadnienie

**Inter-rater reliability**:
- Oblicz zgodność między asesorami (ICC - Intraclass Correlation)
- Jeśli ICC < 0.70, przeprowadź sesję kalibracyjną między asesorami
- Cel: ICC > 0.80

### KROK 3: Uruchomienie systemu AI na tych samych danych

**Cel**: Uzyskać oceny AI dla tych samych odpowiedzi.

**Jak to zrobić**:

```bash
# Uruchom skrypt kalibracyjny
python calibration/run_calibration.py --input calibration_data/ --output calibration_results.json
```

System przetworzy wszystkie odpowiedzi i zapisze wyniki w formacie JSON.

### KROK 4: Analiza porównawcza

**Cel**: Porównać oceny AI z ocenami asesorów i zidentyfikować rozbieżności.

**Metryki do obliczenia**:

1. **Korelacja Pearsona** (ogólna zgodność)
   ```python
   from scipy.stats import pearsonr
   correlation, p_value = pearsonr(assessor_scores, ai_scores)
   ```

2. **Mean Absolute Error** (średnia różnica)
   ```python
   mae = np.mean(np.abs(assessor_scores - ai_scores))
   ```

3. **Confusion Matrix poziomów** (zgodność kategorii)
   - Nieefektywny vs Bazowy vs Efektywny vs Biegły

4. **Analiza wymiarów** (które wymiary są najbardziej rozbieżne)
   ```python
   for dimension in dimensions:
       dim_mae = np.mean(np.abs(assessor_dim[dimension] - ai_dim[dimension]))
   ```

### KROK 5: Dostosowanie wag

**Cel**: Zmodyfikować wagi wymiarów aby poprawić zgodność z asesorami.

**Strategia dostosowania**:

1. **Identyfikuj wymiary z największymi rozbieżnościami**
   - Jeśli AI systematycznie zawyża wymiar → zmniejsz wagę
   - Jeśli AI systematycznie zaniża wymiar → zwiększ wagę

2. **Zachowaj sumę wag = 1.0**
   ```python
   # Przykład: jeśli zwiększasz wagę "intencja" o 0.05
   # musisz zmniejszyć inne wagi proporcjonalnie
   ```

3. **Iteruj**:
   - Zmień wagi w `config/weights.json`
   - Uruchom ponownie system na danych kalibracyjnych
   - Sprawdź metryki
   - Powtarzaj aż osiągniesz cel (korelacja > 0.85, MAE < 0.5)

**Przykład dostosowania**:

```json
// Przed kalibracją
{
  "intencja": 0.10,
  "stan_docelowy": 0.20,
  "metoda_pomiaru": 0.15,
  ...
}

// Po kalibracji (jeśli AI niedoceniało "intencja")
{
  "intencja": 0.15,  // +0.05
  "stan_docelowy": 0.18,  // -0.02
  "metoda_pomiaru": 0.13,  // -0.02
  ...
}
```

### KROK 6: Walidacja krzyżowa

**Cel**: Upewnić się że nowe wagi działają na nowych danych.

**Jak to zrobić**:

1. Zbierz nowy zestaw 10-15 odpowiedzi (nie używanych w kalibracji)
2. Oceń je przez asesorów
3. Oceń je przez system AI (z nowymi wagami)
4. Sprawdź metryki - powinny być podobne lub lepsze niż w kalibracji

---

## Template do zbierania ocen asesorów

Utwórz plik Excel `calibration_template.xlsx` z następującymi kolumnami:

| Response ID | Asesor | Ocena końcowa (0-4) | Intencja (0-1) | Stan docelowy (0-1) | Metoda pomiaru (0-1) | Poziom odpowiedzialności (0-1) | Harmonogram (0-1) | Monitorowanie (0-1) | Sprawdzenie zrozumienia (0-1) | Uzasadnienie |
|-------------|--------|---------------------|----------------|---------------------|----------------------|-------------------------------|-------------------|---------------------|-------------------------------|--------------|
| response_001 | Asesor1 | 2.75 | 0.8 | 0.9 | 0.7 | 0.65 | 0.75 | 0.8 | 0.6 | Jasno określa stan docelowy... |
| response_001 | Asesor2 | 2.5 | 0.7 | 0.85 | 0.65 | 0.7 | 0.7 | 0.75 | 0.65 | Dobra struktura ale... |
| response_002 | Asesor1 | ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

## Skrypt kalibracyjny

Utwórz plik `calibration/run_calibration.py`:

```python
"""
Skrypt do uruchamiania kalibracji systemu
"""

import asyncio
import json
from pathlib import Path
from app.modules.parser import ResponseParser
from app.modules.mapper import ResponseMapper
from app.modules.scorer import CompetencyScorer
from app.modules.feedback import FeedbackGenerator


async def assess_response(response_text: str, response_id: str):
    """Ocenia pojedynczą odpowiedź"""
    parser = ResponseParser()
    mapper = ResponseMapper()
    scorer = CompetencyScorer()
    
    parsed = await parser.parse(response_text)
    mapped = await mapper.map(parsed)
    scoring_result = await scorer.score(mapped)
    
    return {
        "response_id": response_id,
        "score": scoring_result.ocena_delegowanie,
        "level": scoring_result.poziom,
        "dimension_scores": {
            k: v.ocena for k, v in scoring_result.dimension_scores.items()
        }
    }


async def run_calibration(input_dir: Path, output_file: Path):
    """Uruchamia kalibrację na wszystkich plikach w katalogu"""
    results = []
    
    for response_file in sorted(input_dir.glob("*.txt")):
        print(f"Przetwarzanie: {response_file.name}")
        
        with open(response_file, "r", encoding="utf-8") as f:
            response_text = f.read()
        
        result = await assess_response(response_text, response_file.stem)
        results.append(result)
    
    # Zapisz wyniki
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nWyniki zapisane do: {output_file}")
    print(f"Przetworzono {len(results)} odpowiedzi")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Katalog z odpowiedziami")
    parser.add_argument("--output", required=True, help="Plik wyjściowy JSON")
    args = parser.parse_args()
    
    asyncio.run(run_calibration(
        Path(args.input),
        Path(args.output)
    ))
```

---

## Analiza wyników kalibracji

Utwórz plik `calibration/analyze_results.py`:

```python
"""
Skrypt do analizy wyników kalibracji
"""

import json
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import confusion_matrix, mean_absolute_error


def load_assessor_scores(excel_file: str) -> pd.DataFrame:
    """Wczytuje oceny asesorów z Excel"""
    df = pd.read_excel(excel_file)
    # Uśrednij oceny od różnych asesorów
    return df.groupby('Response ID').mean()


def load_ai_scores(json_file: str) -> pd.DataFrame:
    """Wczytuje oceny AI z JSON"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    return pd.DataFrame(data).set_index('response_id')


def analyze_calibration(assessor_file: str, ai_file: str):
    """Analizuje zgodność między asesorami a AI"""
    
    assessors = load_assessor_scores(assessor_file)
    ai = load_ai_scores(ai_file)
    
    # Połącz dane
    merged = assessors.join(ai, rsuffix='_ai')
    
    # 1. Korelacja Pearsona
    correlation, p_value = pearsonr(
        merged['Ocena końcowa (0-4)'],
        merged['score']
    )
    print(f"Korelacja Pearsona: {correlation:.3f} (p={p_value:.4f})")
    
    # 2. Mean Absolute Error
    mae = mean_absolute_error(
        merged['Ocena końcowa (0-4)'],
        merged['score']
    )
    print(f"Mean Absolute Error: {mae:.3f}")
    
    # 3. Analiza wymiarów
    print("\nMAE per wymiar:")
    dimensions = [
        'Intencja', 'Stan docelowy', 'Metoda pomiaru',
        'Poziom odpowiedzialności', 'Harmonogram',
        'Monitorowanie', 'Sprawdzenie zrozumienia'
    ]
    
    for dim in dimensions:
        dim_col = f"{dim} (0-1)"
        dim_ai_col = dim.lower().replace(' ', '_')
        
        if dim_col in merged.columns:
            dim_mae = mean_absolute_error(
                merged[dim_col],
                merged['dimension_scores'].apply(lambda x: x.get(dim_ai_col, 0))
            )
            print(f"  {dim}: {dim_mae:.3f}")
    
    # 4. Rekomendacje
    print("\n=== REKOMENDACJE ===")
    if correlation < 0.85:
        print("⚠ Korelacja poniżej celu (0.85). Dostosuj wagi wymiarów.")
    if mae > 0.5:
        print("⚠ MAE powyżej celu (0.5). System systematycznie odbiega od asesorów.")
    if correlation >= 0.85 and mae <= 0.5:
        print("✓ System dobrze skalibrowany!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--assessors", required=True, help="Plik Excel z ocenami asesorów")
    parser.add_argument("--ai", required=True, help="Plik JSON z ocenami AI")
    args = parser.parse_args()
    
    analyze_calibration(args.assessors, args.ai)
```

---

## Harmonogram kalibracji

| Krok | Czas | Odpowiedzialny |
|------|------|----------------|
| Zebranie 20-30 odpowiedzi | 1-2 tygodnie | HR / Organizator assessmentu |
| Ocena przez asesorów | 3-5 dni | 2-3 asesorów |
| Uruchomienie AI | 1 dzień | Data Scientist / Developer |
| Analiza wyników | 1 dzień | Data Scientist |
| Dostosowanie wag | 2-3 dni | Data Scientist (iteracyjnie) |
| Walidacja krzyżowa | 3-5 dni | Asesorzy + Developer |
| **RAZEM** | **2-3 tygodnie** | |

---

## Kryteria akceptacji

System jest gotowy do produkcji gdy:

✅ Korelacja Pearsona > 0.85  
✅ Mean Absolute Error < 0.5 punktu  
✅ Zgodność poziomów ±1 poziom w > 85% przypadków  
✅ Walidacja krzyżowa potwierdza stabilność  
✅ HR i compliance akceptują transparentność systemu  

---

## Utrzymanie kalibracji

**Po wdrożeniu**:

1. **Monitoring ciągły**: Co kwartał sprawdzaj 10-15 losowych ocen vs asesorzy
2. **Re-kalibracja**: Jeśli metryki spadną poniżej progów, uruchom ponownie kalibrację
3. **Dokumentacja zmian**: Każda zmiana wag musi być udokumentowana w `config/weights.json`

**Wersjonowanie wag**:
```json
{
  "version": "1.1",
  "date": "2026-03-15",
  "calibration_metrics": {
    "correlation": 0.87,
    "mae": 0.42
  },
  "delegowanie": {
    "intencja": 0.15,
    ...
  }
}
```
