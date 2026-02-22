# 📖 Indeks Dokumentacji - System Oceny LEM

**Witaj w systemie automatycznej oceny kompetencji menedżerskich LEM!**

Ten plik pomoże Ci szybko znaleźć właściwą dokumentację.

---

## 🎯 Jestem nowy - od czego zacząć?

### 1️⃣ Przeczytaj to najpierw

**[README.md](README.md)** - Główny przegląd projektu (5 min)
- Co to jest ten system?
- Jakie ma funkcje?
- Podstawowe informacje

### 2️⃣ Zainstaluj system

**[INSTALLATION.md](INSTALLATION.md)** - Szczegółowa instalacja (10 min)
- Wymagania systemowe
- Krok po kroku instalacja
- Konfiguracja OpenAI API
- Troubleshooting

### 3️⃣ Pierwsze uruchomienie

**[QUICKSTART.md](QUICKSTART.md)** - Szybki start (5 min)
- Pierwsze uruchomienie w 5 minut
- Test na przykładowych danych
- Pierwsze zapytanie API
- Interpretacja wyniku

---

## 👨‍💻 Jestem developerem

### Architektura techniczna

**[ARCHITECTURE.md](ARCHITECTURE.md)** - Szczegóły techniczne (15 min)
- Architektura 4 modułów
- Przepływ danych
- Diagramy sekwencji i klas
- Decyzje architektoniczne
- Skalowalność

### Kod źródłowy

| Moduł | Plik | Opis |
|-------|------|------|
| **API** | `app/main.py` | FastAPI server z endpoints |
| **Modele** | `app/models.py` | 8 Pydantic models |
| **Rubryka** | `app/rubric.py` | 7 wymiarów Delegowanie |
| **Parser** | `app/modules/parser.py` | Strukturyzacja odpowiedzi |
| **Mapper** | `app/modules/mapper.py` | Ekstrakcja cytatów |
| **Scorer** | `app/modules/scorer.py` | Algorytm oceny |
| **Feedback** | `app/modules/feedback.py` | Generator feedbacku |

### Testy

- `tests/test_parser.py` - Testy Parsera
- `tests/test_scorer.py` - Testy Scorera
- `tests/test_integration.py` - Testy end-to-end
- `tests/run_manual_test.py` - Manualny test

---

## 🎓 Jestem asesorem / HR

### Jak działa system?

**[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Podsumowanie projektu (10 min)
- Cel projektu
- Co zostało zbudowane
- Kluczowe cechy
- Metryki sukcesu
- Roadmap

### Kalibracja z asesorami

**[CALIBRATION_GUIDE.md](CALIBRATION_GUIDE.md)** - Instrukcja kalibracji (20 min)
- Proces kalibracji krok po kroku
- Zebranie danych referencyjnych
- Ocena przez asesorów
- Analiza zgodności AI vs asesorzy
- Dostosowanie wag
- Template do zbierania ocen

### Narzędzia kalibracji

- `calibration/run_calibration.py` - Uruchom AI na danych
- `calibration/analyze_results.py` - Analizuj zgodność
- `calibration/README.md` - Instrukcja użycia

---

## 📊 Chcę zrozumieć rubrycę

### Rubryka kompetencji

**Plik**: `app/rubric.py`

**7 wymiarów Delegowanie**:
1. **Intencja** (10%) - Nadawanie sensu biznesowego
2. **Stan docelowy** (20%) - Precyzja opisu rezultatu
3. **Metoda pomiaru** (15%) - Wskaźniki/produkty/zachowania
4. **Poziom odpowiedzialności** (20%) - Delegowanie odpowiedzialności
5. **Harmonogram** (10%) - Konsultacja terminów
6. **Monitorowanie** (10%) - Plan kontroli
7. **Sprawdzenie zrozumienia** (15%) - Pytania otwarte

**Każdy wymiar ma 5 poziomów** (0, 1, 2, 3, 4) z opisami zachowań.

---

## 🔌 Chcę zintegrować API

### Dokumentacja API

**Swagger UI**: http://localhost:8000/docs (gdy serwer działa)

### Główny endpoint

**POST /assess**

```bash
curl -X POST "http://localhost:8000/assess" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "P001",
    "response_text": "Twoja odpowiedź...",
    "case_id": "delegowanie_bnp_v1"
  }'
```

**Response**:
```json
{
  "score": 2.75,
  "level": "Efektywny",
  "evidence": {...},
  "feedback": {...},
  "dimension_scores": {...}
}
```

### Inne endpoints

- `GET /health` - Health check
- `GET /dimensions` - Definicje wymiarów
- `GET /weights` - Wagi wymiarów

---

## 🧪 Chcę przetestować system

### Test manualny (najszybszy)

```bash
python tests/run_manual_test.py
```

Przetestuje 5 przykładowych odpowiedzi i wyświetli szczegółowe wyniki.

### Testy jednostkowe

```bash
# Wszystkie testy
pytest tests/ -v

# Tylko integracyjne
pytest tests/test_integration.py -v -s
```

### Dane testowe

`tests/sample_responses/` zawiera 5 syntetycznych odpowiedzi:
- `response_level_0_nieefektywny.txt` (0.5-1.0)
- `response_level_1_bazowy.txt` (1.0-2.0)
- `response_level_2_efektywny.txt` (2.0-3.0)
- `response_level_2_5_efektywny_plus.txt` (2.5-2.75)
- `response_level_3_biegly.txt` (3.0-4.0)

---

## ⚙️ Chcę skonfigurować system

### Konfiguracja podstawowa

**Plik**: `.env`

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

### Wagi wymiarów

**Plik**: `config/weights.json`

```json
{
  "delegowanie": {
    "intencja": 0.10,
    "stan_docelowy": 0.20,
    "metoda_pomiaru": 0.15,
    "poziom_odpowiedzialnosci": 0.20,
    "harmonogram": 0.10,
    "monitorowanie": 0.10,
    "sprawdzenie_zrozumienia": 0.15
  }
}
```

**Suma wag musi być = 1.0**

### Prompty LLM

- `app/prompts/parse_prompt.txt` - Prompt Parsera
- `app/prompts/map_prompt.txt` - Prompt Mappera
- `app/prompts/feedback_prompt.txt` - Prompt Feedbacku

Możesz edytować te pliki aby dostosować zachowanie systemu.

---

## ❓ Mam problem

### Troubleshooting

Patrz sekcja "Troubleshooting" w:
- **[INSTALLATION.md](INSTALLATION.md)** - Problemy z instalacją
- **[QUICKSTART.md](QUICKSTART.md)** - Problemy z uruchomieniem

### Najczęstsze problemy

| Problem | Rozwiązanie |
|---------|-------------|
| "OPENAI_API_KEY nie jest ustawiony" | Sprawdź plik `.env` |
| "Module not found" | Uruchom `pip install -r requirements.txt` |
| "Address already in use" | Użyj innego portu: `--port 8001` |
| Testy timeout | Sprawdź połączenie z OpenAI |

---

## 📈 Co dalej?

### Następne kroki po instalacji

1. ✅ **Przetestuj** - Uruchom na przykładowych danych
2. ✅ **Kalibruj** - Zbierz oceny asesorów (patrz `CALIBRATION_GUIDE.md`)
3. ✅ **Waliduj** - Potwierdź stabilność metryk
4. ✅ **Skaluj** - Dodaj 3 pozostałe kompetencje LEM
5. ✅ **Integruj** - Połącz z platformą testową

### Roadmap projektu

Patrz sekcja "Roadmap" w **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**

---

## 📁 Struktura projektu

```
lem-assessment/
├── app/                    # Kod źródłowy
│   ├── main.py            # FastAPI server
│   ├── models.py          # Pydantic models
│   ├── rubric.py          # Rubryka kompetencji
│   ├── modules/           # 4 moduły przetwarzania
│   └── prompts/           # Prompty LLM
├── tests/                 # Testy
│   ├── test_*.py         # Testy jednostkowe
│   └── sample_responses/ # Dane testowe
├── calibration/          # Narzędzia kalibracji
├── config/               # Konfiguracja (wagi)
└── *.md                  # Dokumentacja
```

**Statystyki**: 34 pliki, 7 katalogów

---

## 📚 Wszystkie dokumenty

| Dokument | Dla kogo | Czas | Opis |
|----------|----------|------|------|
| **[README.md](README.md)** | Wszyscy | 5 min | Główny przegląd |
| **[INDEX.md](INDEX.md)** | Wszyscy | 3 min | Ten plik - indeks |
| **[QUICKSTART.md](QUICKSTART.md)** | Developerzy | 5 min | Szybki start |
| **[INSTALLATION.md](INSTALLATION.md)** | Developerzy | 10 min | Instalacja |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Developerzy | 15 min | Architektura |
| **[CALIBRATION_GUIDE.md](CALIBRATION_GUIDE.md)** | Asesorzy/HR | 20 min | Kalibracja |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | Wszyscy | 10 min | Podsumowanie |

---

## 🎯 Szybkie linki

### Uruchomienie

```bash
# Instalacja
pip install -r requirements.txt

# Konfiguracja
copy .env.example .env
# Edytuj .env i dodaj OPENAI_API_KEY

# Uruchomienie
uvicorn app.main:app --reload

# Test
python tests/run_manual_test.py
```

### Dokumentacja online

- API Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

**Powodzenia! 🚀**

Jeśli masz pytania, zacznij od przeczytania odpowiedniego dokumentu powyżej.
