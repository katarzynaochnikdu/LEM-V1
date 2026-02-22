# Instrukcja Instalacji - System Oceny LEM

## Wymagania systemowe

- **Python**: 3.11 lub nowszy
- **System operacyjny**: Windows 10/11, macOS, Linux
- **RAM**: minimum 4GB
- **Dysk**: ~500MB (zależności + projekt)
- **Internet**: wymagany (API OpenAI)

## Krok 1: Instalacja Python

### Windows

1. Pobierz Python z https://www.python.org/downloads/
2. Uruchom instalator
3. ✅ Zaznacz "Add Python to PATH"
4. Kliknij "Install Now"

Weryfikacja:
```bash
python --version
# Powinno pokazać: Python 3.11.x lub nowszy
```

### macOS

```bash
# Użyj Homebrew
brew install python@3.11
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

## Krok 2: Pobranie projektu

```bash
# Jeśli projekt jest w repozytorium Git
git clone <repository-url>
cd LEM

# Lub po prostu przejdź do katalogu projektu
cd c:\Users\kochn\.cursor\Daniel\LEM
```

## Krok 3: Utworzenie środowiska wirtualnego (opcjonalne, ale zalecane)

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

Po aktywacji powinieneś zobaczyć `(venv)` przed promptem terminala.

## Krok 4: Instalacja zależności

```bash
pip install -r requirements.txt
```

To zainstaluje:
- FastAPI (framework webowy)
- Uvicorn (serwer ASGI)
- Pydantic (walidacja danych)
- OpenAI (API do GPT-4)
- pytest (testy)
- python-dotenv (zmienne środowiskowe)

**Czas instalacji**: 2-5 minut (zależnie od prędkości internetu)

## Krok 5: Konfiguracja OpenAI API

### 5.1. Uzyskanie API key

1. Przejdź do https://platform.openai.com/
2. Zaloguj się lub utwórz konto
3. Przejdź do "API Keys"
4. Kliknij "Create new secret key"
5. Skopiuj klucz (zaczyna się od `sk-...`)

### 5.2. Konfiguracja w projekcie

```bash
# Skopiuj przykładowy plik .env
copy .env.example .env

# Na macOS/Linux:
# cp .env.example .env
```

Edytuj plik `.env` i dodaj swój klucz:

```
OPENAI_API_KEY=sk-twoj-klucz-tutaj
OPENAI_MODEL=gpt-4o
```

**⚠️ WAŻNE**: Nigdy nie commituj pliku `.env` do repozytorium Git!

## Krok 6: Weryfikacja instalacji

### Test 1: Sprawdź czy wszystkie moduły się importują

```bash
python -c "from app.main import app; print('✓ Import OK')"
```

### Test 2: Uruchom testy jednostkowe (opcjonalne)

```bash
pytest tests/test_parser.py -v
```

**Uwaga**: Testy wymagają działającego API key i będą kosztować ~$0.10-0.20.

### Test 3: Uruchom manualny test

```bash
python tests/run_manual_test.py
```

To przetworzy 5 przykładowych odpowiedzi i wyświetli wyniki.

**Oczekiwany output**:
```
================================================================================
TESTOWANIE: response_level_2_efektywny.txt
================================================================================

Długość odpowiedzi: 1234 znaków

MODUŁ 1: Parsowanie...
✓ Sparsowano na 4 sekcje
  - Przygotowanie: 234 znaków
  - Przebieg: 567 znaków
  ...

MODUŁ 2: Mapowanie na wymiary...
✓ Znaleziono 6/7 wymiarów
  ...

MODUŁ 3: Scoring...
✓ Ocena końcowa: 2.75/4.0
  Poziom: Efektywny (Świadoma kompetencja)
  ...

MODUŁ 4: Generowanie feedbacku...
✓ Wygenerowano feedback
  ...
```

## Krok 7: Uruchomienie serwera API

```bash
uvicorn app.main:app --reload
```

**Oczekiwany output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Sprawdź czy API działa

Otwórz przeglądarkę i przejdź do:

1. **Health check**: http://localhost:8000/health
   - Powinno pokazać: `{"status":"healthy","version":"1.0.0",...}`

2. **Dokumentacja API**: http://localhost:8000/docs
   - Interaktywna dokumentacja Swagger UI

3. **Wymiary kompetencji**: http://localhost:8000/dimensions
   - Lista 7 wymiarów delegowania

## Krok 8: Pierwsze zapytanie API

### Przez Swagger UI (najłatwiejsze)

1. Otwórz http://localhost:8000/docs
2. Kliknij na `POST /assess`
3. Kliknij "Try it out"
4. Wklej przykładową odpowiedź w pole `response_text`
5. Kliknij "Execute"

### Przez curl (terminal)

```bash
curl -X POST "http://localhost:8000/assess" \
  -H "Content-Type: application/json" \
  -d "{\"participant_id\":\"TEST001\",\"response_text\":\"Przygotowując się do rozmowy delegującej analizuję priorytety kwartalne banku. Wybieram projekt poprawy jakości obsługi klientów. W rozmowie zaczynam od wyjaśnienia kontekstu biznesowego - centrala wyznaczyła nowe priorytety. Przedstawiam konkretne zadanie: wdrożenie nowego procesu obsługi reklamacji. Określam stan docelowy: proces ma być gotowy do 31 marca, czas obsługi ma spaść z 5 do 3 dni. Wyjaśniam metodę pomiaru: będziemy śledzić średni czas obsługi oraz NPS. Ustalamy harmonogram wspólnie z pracownikiem. Określam punkty kontrolne: spotkania co dwa tygodnie. Pytam pracownika: Jak rozumiesz cel tego projektu? Jakie widzisz wyzwania?\",\"case_id\":\"delegowanie_bnp_v1\"}"
```

### Przez Python

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
```

## Troubleshooting

### Problem: "python: command not found"

**Rozwiązanie**:
- Windows: Użyj `py` zamiast `python`
- macOS/Linux: Użyj `python3` zamiast `python`

### Problem: "pip: command not found"

**Rozwiązanie**:
```bash
# Windows
py -m pip install -r requirements.txt

# macOS/Linux
python3 -m pip install -r requirements.txt
```

### Problem: "ModuleNotFoundError: No module named 'fastapi'"

**Rozwiązanie**: Zależności nie zostały zainstalowane
```bash
pip install -r requirements.txt
```

### Problem: "OPENAI_API_KEY nie jest ustawiony"

**Rozwiązanie**:
1. Sprawdź czy plik `.env` istnieje w głównym katalogu
2. Sprawdź czy zawiera linię: `OPENAI_API_KEY=sk-...`
3. Upewnij się że klucz jest poprawny (skopiowany z OpenAI)

### Problem: "Address already in use" przy uruchomieniu uvicorn

**Rozwiązanie**: Port 8000 jest zajęty
```bash
# Użyj innego portu
uvicorn app.main:app --reload --port 8001
```

### Problem: Testy kończą się błędem "Timeout"

**Rozwiązanie**: API OpenAI może być wolne lub niedostępne
- Sprawdź połączenie internetowe
- Sprawdź status OpenAI: https://status.openai.com/
- Zwiększ timeout w testach (edytuj `pytest.ini`)

### Problem: Wysokie koszty API

**Rozwiązanie**:
- Ustaw limity w OpenAI dashboard: https://platform.openai.com/account/limits
- Używaj tylko przykładowych odpowiedzi do testów
- Rozważ użycie cache'owania (przyszła funkcjonalność)

## Deinstalacja

### Usunięcie środowiska wirtualnego

```bash
# Windows
deactivate
rmdir /s venv

# macOS/Linux
deactivate
rm -rf venv
```

### Usunięcie zależności globalnych (jeśli nie używałeś venv)

```bash
pip uninstall -r requirements.txt -y
```

## Aktualizacja

### Aktualizacja zależności

```bash
pip install --upgrade -r requirements.txt
```

### Aktualizacja projektu (jeśli w Git)

```bash
git pull
pip install -r requirements.txt  # Na wypadek nowych zależności
```

## Następne kroki

Po udanej instalacji:

1. 📖 Przeczytaj `QUICKSTART.md` - szybki start (5 minut)
2. 🧪 Przetestuj na własnych odpowiedziach
3. 🎯 Przejdź do kalibracji (patrz `CALIBRATION_GUIDE.md`)
4. 🏗 Rozważ integrację z platformą testową

## Wsparcie

Jeśli masz problemy z instalacją:

1. Sprawdź sekcję Troubleshooting powyżej
2. Przeczytaj `README.md` - główna dokumentacja
3. Sprawdź logi w terminalu gdzie uruchomiłeś `uvicorn`

## Checklist instalacji

- [ ] Python 3.11+ zainstalowany
- [ ] Projekt pobrany/sklonowany
- [ ] Środowisko wirtualne utworzone (opcjonalne)
- [ ] Zależności zainstalowane (`pip install -r requirements.txt`)
- [ ] Plik `.env` utworzony z OpenAI API key
- [ ] Test manualny przeszedł (`python tests/run_manual_test.py`)
- [ ] Serwer API działa (`uvicorn app.main:app --reload`)
- [ ] Swagger UI dostępne (http://localhost:8000/docs)
- [ ] Pierwsze zapytanie API zakończone sukcesem

**Jeśli wszystkie punkty są zaznaczone - instalacja zakończona! ✅**
