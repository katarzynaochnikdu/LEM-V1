# Katalog Kalibracji

Ten katalog zawiera narzędzia do kalibracji systemu oceny LEM.

## Pliki

- `run_calibration.py` - Uruchamia system AI na zestawie odpowiedzi
- `analyze_results.py` - Analizuje zgodność między AI a asesorami
- `README.md` - Ten plik

## Użycie

### 1. Przygotuj dane

Utwórz katalog `calibration_data/` z plikami tekstowymi zawierającymi odpowiedzi:

```
calibration_data/
├── response_001.txt
├── response_002.txt
└── ...
```

### 2. Uruchom system AI

```bash
python calibration/run_calibration.py --input calibration_data/ --output results/ai_scores.json
```

### 3. Przygotuj oceny asesorów

Utwórz plik Excel `assessor_scores.xlsx` z kolumnami:
- Response ID
- Asesor
- Ocena końcowa (0-4)
- Intencja (0-1)
- Stan docelowy (0-1)
- ... (pozostałe wymiary)

### 4. Analizuj wyniki

```bash
python calibration/analyze_results.py --assessors assessor_scores.xlsx --ai results/ai_scores.json
```

### 5. Dostosuj wagi

Na podstawie analizy, edytuj `config/weights.json` i powtórz kroki 2-4.

## Wymagane biblioteki

Dla `analyze_results.py` potrzebne są dodatkowe biblioteki:

```bash
pip install pandas openpyxl scipy scikit-learn
```

## Cel kalibracji

- Korelacja Pearsona > 0.85
- Mean Absolute Error < 0.5
- Zgodność poziomów ±1 > 85%
