import httpx
import json

response_text = """Przygotowanie do rozmowy:
Przygotowuję się szczegółowo do rozmowy delegującej. Analizuję nowe priorytety kwartalne 
(wzrost przychodów z segmentu detalicznego, poprawa omnichanelowej jakości obsługi, 
skrócenie czasu decyzyjnego) i wybieram projekt który bezpośrednio wspiera cel poprawy 
jakości obsługi. Przygotowuję konkretny opis stanu docelowego: chcę aby do końca marca 
wdrożyć nowy proces obsługi reklamacji, który skróci czas odpowiedzi z 5 do 3 dni roboczych. 
Planuję również jak będę mierzyć sukces - przez wskaźnik NPS i czas obsługi reklamacji.

Przebieg rozmowy:
1. Zaczynam od wyjaśnienia kontekstu biznesowego - centrala wyznaczyła nowe priorytety 
   i musimy się do nich dostosować
2. Przedstawiam konkretne zadanie: Chcę abyś poprowadził projekt wdrożenia nowego procesu 
   obsługi reklamacji
3. Określam stan docelowy: proces ma być gotowy do 31 marca, czas obsługi reklamacji 
   ma spaść z 5 do 3 dni
4. Wyjaśniam metodę pomiaru: będziemy śledzić średni czas obsługi reklamacji oraz wynik NPS
5. Ustalamy harmonogram: wspólnie z pracownikiem ustalamy kamienie milowe
6. Określam punkty kontrolne: spotkania co dwa tygodnie aby omówić postępy
7. Pytam pracownika: Jak rozumiesz cel tego projektu? Jakie widzisz wyzwania?

Decyzje delegacyjne:
Wybieram młodszego pracownika który ma potencjał ale brakuje mu pewności. To zadanie 
o średnim poziomie ryzyka. Decyduję że dam mu odpowiedzialność za cały proces wdrożenia.

Planowane efekty:
Pracownik dostarczy działający proces obsługi reklamacji do 31 marca.
Czas obsługi reklamacji spadnie z 5 do 3 dni roboczych.
Pracownik nabierze doświadczenia w prowadzeniu projektów procesowych."""

resp = httpx.post(
    "http://localhost:8001/assess",
    json={
        "participant_id": "TEST_SERWER_001",
        "response_text": response_text,
        "case_id": "delegowanie_bnp_v1"
    },
    timeout=120
)

result = resp.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
