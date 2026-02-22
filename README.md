# System Oceny Kompetencji LEM - MVP

> **Automatyczny, audytowalny system oceny kompetencji menedżerskich z wykorzystaniem AI**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-orange.svg)](https://openai.com/)

---

## 🎯 Czym jest ten system?

System automatycznie ocenia odpowiedzi narracyjne uczestników assessmentu menedżerskiego w zakresie kompetencji **Delegowanie** według modelu LEM. 

**Kluczowe cechy**:
- ✅ Ocena 0-4 (co 0.25 punktu) oparta na eksperckiej rubryce 7 wymiarów
- ✅ Ekstrakcja cytatów-dowodów z odpowiedzi (pełna audytowalność)
- ✅ Spersonalizowany feedback rozwojowy
- ✅ Transparentny breakdown oceny na wymiary
- ✅ API gotowe do integracji

---

## 🚀 Szybki start (5 minut)

### 1. Instalacja

```bash
# Sklonuj projekt
cd c:\Users\kochn\.cursor\Daniel\LEM

# Zainstaluj zależności
pip install -r requirements.txt

# Skonfiguruj API key
copy .env.example .env
# Edytuj .env i dodaj: OPENAI_API_KEY=sk-...
```

### 2. Uruchomienie

```bash
# Uruchom serwer
uvicorn app.main:app --reload

# Otwórz dokumentację API
# http://localhost:8000/docs
```

### 3. Test

```bash
# Uruchom test na przykładowych odpowiedziach
python tests/run_manual_test.py
```

**Szczegółowa instrukcja**: Patrz [`QUICKSTART.md`](QUICKSTART.md) lub [`INSTALLATION.md`](INSTALLATION.md)

---

## 📚 Dokumentacja

| Dokument | Opis | Czas czytania |
|----------|------|---------------|
| **[QUICKSTART.md](QUICKSTART.md)** | Szybki start - pierwsze uruchomienie | 5 min |
| **[INSTALLATION.md](INSTALLATION.md)** | Szczegółowa instrukcja instalacji | 10 min |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Architektura techniczna systemu | 15 min |
| **[CALIBRATION_GUIDE.md](CALIBRATION_GUIDE.md)** | Instrukcja kalibracji z asesorami | 20 min |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | Podsumowanie projektu | 10 min |

---

## 🏗 Architektura

System składa się z **4 modułów** przetwarzania sekwencyjnego:

```
Odpowiedź → [Parser] → [Mapper] → [Scorer] → [Feedback] → Ocena + Feedback
            ↓           ↓           ↓           ↓
         Strukturyzacja Ekstrakcja  Algorytm   Personalizacja
         na sekcje      cytatów     oceny      feedbacku
```

### Moduły

1. **Parser** (`app/modules/parser.py`) - Strukturyzacja odpowiedzi na 4 sekcje logiczne
2. **Mapper** (`app/modules/mapper.py`) - Ekstrakcja cytatów dla 7 wymiarów delegowania
3. **Scorer** (`app/modules/scorer.py`) - Algorytm oceny 0-4 z wagami wymiarów
4. **Feedback Generator** (`app/modules/feedback.py`) - Generowanie spersonalizowanego feedbacku

**Szczegóły**: Patrz [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## 📊 7 Wymiarów Delegowania

System ocenia odpowiedzi według 7 wymiarów kompetencji Delegowanie:

| Wymiar | Waga | Opis |
|--------|------|------|
| **Intencja** | 10% | Nadawanie sensu biznesowego zadaniu |
| **Stan docelowy** | 20% | Precyzja opisu rezultatu końcowego |
| **Metoda pomiaru** | 15% | Wskaźniki/produkty/zachowania |
| **Poziom odpowiedzialności** | 20% | Delegowanie odpowiedzialności, nie tylko zadań |
| **Harmonogram** | 10% | Konsultacja terminów z pracownikiem |
| **Monitorowanie** | 10% | Plan kontroli przebiegu |
| **Sprawdzenie zrozumienia** | 15% | Pytania otwarte o rozumienie |

**Rubryka szczegółowa**: Patrz [`app/rubric.py`](app/rubric.py)

---

## 🔌 API Endpoints

### `POST /assess` - Główny endpoint oceny

**Request**:
```json
{
  "participant_id": "P001",
  "response_text": "Przygotowując się do rozmowy delegującej...",
  "case_id": "delegowanie_bnp_v1"
}
```

**Response**:
```json
{
  "participant_id": "P001",
  "timestamp": "2026-02-22T10:30:00Z",
  "competency": "delegowanie",
  "score": 2.75,
  "level": "Efektywny (Świadoma kompetencja)",
  "evidence": {
    "intencja": ["Wyjaśniam kontekst biznesowy..."],
    "stan_docelowy": ["Proces ma być gotowy do 31 marca..."]
  },
  "feedback": {
    "summary": "Precyzyjnie definiujesz stan docelowy...",
    "recommendation": "Wzmocnij delegowanie odpowiedzialności...",
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

### Inne endpointy

- `GET /health` - Health check
- `GET /dimensions` - Definicje wymiarów
- `GET /weights` - Aktualne wagi wymiarów

**Dokumentacja interaktywna**: http://localhost:8000/docs (gdy serwer działa)

---

## 🧪 Testy

### Testy jednostkowe

```bash
# Wszystkie testy
pytest tests/ -v

# Tylko Parser
pytest tests/test_parser.py -v

# Tylko Scorer
pytest tests/test_scorer.py -v

# Testy integracyjne (end-to-end)
pytest tests/test_integration.py -v -s
```

### Test manualny

```bash
# Przetestuj na 5 przykładowych odpowiedziach
python tests/run_manual_test.py
```

**Dane testowe**: 5 syntetycznych odpowiedzi w `tests/sample_responses/`

---

## 📂 Struktura projektu

```
lem-assessment/
├── app/
│   ├── main.py                    # FastAPI server
│   ├── models.py                  # Pydantic models (8 modeli)
│   ├── rubric.py                  # Rubryka Delegowanie (7 wymiarów)
│   ├── modules/
│   │   ├── parser.py              # Moduł 1: Strukturyzacja
│   │   ├── mapper.py              # Moduł 2: Ekstrakcja dowodów
│   │   ├── scorer.py              # Moduł 3: Algorytm oceny
│   │   └── feedback.py            # Moduł 4: Generator feedbacku
│   └── prompts/
│       ├── parse_prompt.txt       # Prompt Parsera
│       ├── map_prompt.txt         # Prompt Mappera
│       └── feedback_prompt.txt    # Prompt Feedbacku
├── tests/
│   ├── test_*.py                  # Testy jednostkowe
│   ├── run_manual_test.py         # Skrypt manualnego testu
│   └── sample_responses/          # 5 przykładowych odpowiedzi
├── calibration/
│   ├── run_calibration.py         # Skrypt kalibracji
│   ├── analyze_results.py         # Analiza wyników
│   └── README.md                  # Instrukcja kalibracji
├── config/
│   └── weights.json               # Wagi wymiarów (kalibrowane)
├── requirements.txt               # Zależności Python
├── .env.example                   # Template zmiennych środowiskowych
└── *.md                           # Dokumentacja
```

**Statystyki**: 34 pliki, 11 modułów Python, 5 dokumentów

---

## 🎯 Kalibracja

System wymaga kalibracji z ocenami asesorów przed wdrożeniem produkcyjnym.

**Proces kalibracji** (2-3 tygodnie):
1. Zebranie 20-30 prawdziwych odpowiedzi
2. Ocena przez 2-3 niezależnych asesorów
3. Uruchomienie systemu AI na tych samych danych
4. Analiza zgodności (cel: korelacja >0.85, MAE <0.5)
5. Dostosowanie wag w `config/weights.json`
6. Walidacja krzyżowa

**Szczegółowa instrukcja**: Patrz [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md)

---

## 💰 Koszty

### Koszty operacyjne (produkcja)

- **Na 1 ocenę**: ~$0.10-0.15 (GPT-4o)
- **Na 100 uczestników**: ~$12
- **Na 1000 uczestników/rok**: ~$120/rok

### Optymalizacje (przyszłość)

- Fine-tuning: -30% kosztów
- Caching: -40% kosztów
- Hybrid approach: -60% kosztów

---

## 🔧 Stack technologiczny

| Warstwa | Technologia | Wersja |
|---------|-------------|--------|
| Backend | FastAPI | 0.115.0 |
| Runtime | Python | 3.11+ |
| LLM | OpenAI GPT-4o | latest |
| Validation | Pydantic | 2.9.2 |
| Testing | pytest | 8.3.3 |
| HTTP | uvicorn + httpx | latest |

---

## 📈 Roadmap

### ✅ MVP (ukończone)

- [x] 4 moduły przetwarzania (Parser, Mapper, Scorer, Feedback)
- [x] API FastAPI z 3 endpoints
- [x] Rubryka 7 wymiarów Delegowanie
- [x] Dane testowe (5 przykładowych odpowiedzi)
- [x] Testy jednostkowe i integracyjne
- [x] Narzędzia kalibracji
- [x] Dokumentacja

### 🔄 Następne kroki

1. **Kalibracja** (2-3 tygodnie) - Dostosowanie wag z asesorami
2. **Walidacja** (1 tydzień) - Potwierdzenie stabilności
3. **Skalowanie** (2-3 tygodnie) - Dodanie 3 pozostałych kompetencji LEM
4. **Integracja** (1-2 tygodnie) - Połączenie z platformą testową

---

## ⚠️ Znane ograniczenia MVP

- ❌ Brak kalibracji - wagi wymiarów są szacunkowe
- ❌ Jedna kompetencja - tylko Delegowanie (3 pozostałe do dodania)
- ❌ Brak cache'owania - każde wywołanie to pełne przetwarzanie
- ❌ Brak rate limiting - API nie ma ograniczeń requestów
- ❌ Brak persystencji - wyniki nie są zapisywane
- ❌ Brak auth - API jest otwarte

---

## 🤝 Wkład i rozwój

### Rozszerzenie na 4 kompetencje

System jest zaprojektowany do łatwego rozszerzenia na pozostałe 3 kompetencje LEM:
- Podejmowanie decyzji na bazie kryteriów
- Określanie celów i priorytetów
- Udzielanie informacji zwrotnej

**Szacunek pracy**: ~40% dodatkowej pracy (głównie rubryki + prompty)

---

## 📞 Wsparcie

### Dokumentacja

- **Quick Start**: [`QUICKSTART.md`](QUICKSTART.md)
- **Instalacja**: [`INSTALLATION.md`](INSTALLATION.md)
- **Architektura**: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Kalibracja**: [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md)
- **Podsumowanie**: [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md)

### API Docs

- Swagger UI: http://localhost:8000/docs (gdy serwer działa)

### Troubleshooting

Patrz sekcja "Troubleshooting" w [`INSTALLATION.md`](INSTALLATION.md)

---

## 📄 Licencja

Proprietary - BNP Paribas

---

## ✨ Podsumowanie

System Oceny LEM MVP jest **w pełni funkcjonalny** i gotowy do:

✅ Testowania na prawdziwych odpowiedziach  
✅ Kalibracji z ocenami asesorów  
✅ Walidacji przez HR i compliance  
✅ Rozszerzenia na 4 kompetencje  

**Kluczowe osiągnięcie**: Transparentny, audytowalny system AI który **wspiera** (nie zastępuje) ekspertów w ocenie kompetencji menedżerskich.

---

**Projekt ukończony! 🎉**  
**Wersja**: 1.0.0  
**Data**: 22 lutego 2026
