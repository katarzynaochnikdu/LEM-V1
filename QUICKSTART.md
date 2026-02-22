# Quick Start - System Oceny LEM

Szybki start dla systemu automatycznej oceny kompetencji Delegowanie.

## 1. Instalacja (5 minut)

### Wymagania
- Python 3.11+
- OpenAI API key

### Kroki instalacji

```bash
# 1. Sklonuj/pobierz projekt
cd c:\Users\kochn\.cursor\Daniel\LEM

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Utwórz plik .env
copy .env.example .env

# 4. Edytuj .env i dodaj swój OpenAI API key
# OPENAI_API_KEY=sk-...
```

## 2. Pierwsze uruchomienie (2 minuty)

### Test manualny

```bash
# Uruchom test na przykładowych odpowiedziach
python tests/run_manual_test.py
```

To przetworzy 5 przykładowych odpowiedzi i wyświetli szczegółowe wyniki.

### Uruchomienie API

```bash
# Uruchom serwer FastAPI
uvicorn app.main:app --reload
```

API będzie dostępne pod: `http://localhost:8000`

Dokumentacja Swagger: `http://localhost:8000/docs`

## 3. Pierwsze zapytanie API (1 minuta)

### Przykład curl

```bash
curl -X POST "http://localhost:8000/assess" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "TEST001",
    "response_text": "Przygotowując się do rozmowy delegującej analizuję priorytety kwartalne banku. Wybieram projekt poprawy jakości obsługi klientów. W rozmowie zaczynam od wyjaśnienia kontekstu biznesowego - centrala wyznaczyła nowe priorytety. Przedstawiam konkretne zadanie: wdrożenie nowego procesu obsługi reklamacji. Określam stan docelowy: proces ma być gotowy do 31 marca, czas obsługi ma spaść z 5 do 3 dni. Wyjaśniam metodę pomiaru: będziemy śledzić średni czas obsługi oraz NPS. Ustalamy harmonogram wspólnie z pracownikiem. Określam punkty kontrolne: spotkania co dwa tygodnie. Pytam pracownika: Jak rozumiesz cel tego projektu? Jakie widzisz wyzwania?",
    "case_id": "delegowanie_bnp_v1"
  }'
```

### Przykład Python

```python
import requests

response = requests.post(
    "http://localhost:8000/assess",
    json={
        "participant_id": "TEST001",
        "response_text": "Twoja odpowiedź tutaj...",
        "case_id": "delegowanie_bnp_v1"
    }
)

result = response.json()
print(f"Ocena: {result['score']}/4.0")
print(f"Poziom: {result['level']}")
print(f"Feedback: {result['feedback']['summary']}")
```

## 4. Interpretacja wyniku

Przykładowa odpowiedź API:

```json
{
  "participant_id": "TEST001",
  "timestamp": "2026-02-22T10:30:00Z",
  "competency": "delegowanie",
  "score": 2.75,
  "level": "Efektywny (Świadoma kompetencja)",
  "evidence": {
    "intencja": ["Wyjaśniam kontekst biznesowy..."],
    "stan_docelowy": ["Proces ma być gotowy do 31 marca..."],
    ...
  },
  "feedback": {
    "summary": "Precyzyjnie definiujesz stan docelowy i metodę pomiaru...",
    "recommendation": "Wzmocnij delegowanie odpowiedzialności procesowej...",
    "mocne_strony": [...],
    "obszary_rozwoju": [...]
  },
  "dimension_scores": {
    "intencja": 0.8,
    "stan_docelowy": 0.9,
    ...
  }
}
```

### Skala ocen

- **0.0 - 0.99**: Nieefektywny (Nieświadoma niekompetencja)
- **1.0 - 1.99**: Bazowy (Świadoma niekompetencja)
- **2.0 - 2.99**: Efektywny (Świadoma kompetencja)
- **3.0 - 4.0**: Biegły (Nieświadoma kompetencja)

## 5. Testy (opcjonalne)

```bash
# Uruchom testy jednostkowe
pytest tests/ -v

# Uruchom tylko testy integracyjne
pytest tests/test_integration.py -v -s
```

## 6. Następne kroki

1. **Testowanie**: Przetestuj na prawdziwych odpowiedziach
2. **Kalibracja**: Zbierz oceny asesorów i uruchom kalibrację (patrz `CALIBRATION_GUIDE.md`)
3. **Integracja**: Połącz z platformą testową uczestników
4. **Skalowanie**: Dodaj pozostałe 3 kompetencje LEM

## Troubleshooting

### Błąd: "OPENAI_API_KEY nie jest ustawiony"
- Sprawdź czy plik `.env` istnieje
- Sprawdź czy zawiera `OPENAI_API_KEY=sk-...`
- Upewnij się że klucz jest poprawny

### Błąd: "Module not found"
- Uruchom `pip install -r requirements.txt`
- Sprawdź czy jesteś w głównym katalogu projektu

### API zwraca błąd 500
- Sprawdź logi w terminalu gdzie uruchomiłeś `uvicorn`
- Sprawdź czy OpenAI API key jest poprawny
- Sprawdź czy masz dostęp do internetu (API OpenAI)

## Pomoc

- Dokumentacja pełna: `README.md`
- Instrukcja kalibracji: `CALIBRATION_GUIDE.md`
- API docs: `http://localhost:8000/docs` (gdy serwer działa)
