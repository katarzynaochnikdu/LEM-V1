"""
Rubryka oceny kompetencji menedżerskich - System LEM
Obsługuje 4 kompetencje: Delegowanie, Podejmowanie decyzji, Określanie priorytetów, Informacja zwrotna
Oparta na dokumentacji 4 LEM.pdf

Definicje ładowane z config/competencies/*.json (edytowalne, wersjonowane).
Hardkodowane stałe poniżej służą wyłącznie jako fallback.
"""

import json
from pathlib import Path
from typing import Dict, List
from enum import Enum

COMPETENCIES_DIR = Path(__file__).parent.parent / "config" / "competencies"


class PoziomKompetencji(str, Enum):
    """Poziomy kompetencji według skali LEM"""
    NIEEFEKTYWNY = "Nieefektywny (Nieświadoma niekompetencja)"
    BAZOWY = "Bazowy (Świadoma niekompetencja)"
    EFEKTYWNY = "Efektywny (Świadoma kompetencja)"
    BIEGLY = "Biegły (Nieświadoma kompetencja)"


# ---------------------------------------------------------------------------
# KOMPETENCJA 1: DELEGOWANIE (7 wymiarów)
# ---------------------------------------------------------------------------

ALGORYTM_DELEGOWANIE = [
    "1. Nadaj intencje",
    "2. Wyznacz poziom odpowiedzialności",
    "3. Określ stan docelowy",
    "4. Ustal metodę pomiaru",
    "5. Określ proces monitorowania",
    "6. Zaplanuj harmonogram",
    "7. Sprawdź jak pracownik rozumie proces wykonania"
]

WYMIARY_DELEGOWANIE = {
    "intencja": {
        "nazwa": "Nadawanie intencji biznesowej",
        "opis": "Czy menedżer nadaje sens strategiczny i biznesowy delegowanemu zadaniu",
        "poziomy": {
            0.0: {
                "opis": "Nie określa intencji zadania, brak kontekstu biznesowego",
                "zachowania": [
                    "Nie wyjaśnia po co zadanie jest wykonywane",
                    "Brak powiązania z celami biznesowymi",
                    "Zadanie bez kontekstu strategicznego"
                ]
            },
            1.0: {
                "opis": "Ustala intencje w sposób ogólny ('mamy problem, proszę się tym zająć')",
                "zachowania": [
                    "Ogólnikowe wyjaśnienie celu",
                    "Brak precyzji w opisie znaczenia zadania",
                    "Minimalne odniesienie do kontekstu biznesowego"
                ]
            },
            2.0: {
                "opis": "Jasno określa intencję biznesową zadania",
                "zachowania": [
                    "Wyjaśnia cel biznesowy zadania",
                    "Wskazuje znaczenie dla zespołu/organizacji",
                    "Komunikuje kontekst podejmowanych działań"
                ]
            },
            3.0: {
                "opis": "Intencja + powiązanie ze strategią organizacji",
                "zachowania": [
                    "Łączy zadanie ze strategią organizacji",
                    "Wyjaśnia wpływ na kluczowe cele kwartalne/roczne",
                    "Pokazuje szerszy kontekst biznesowy"
                ]
            },
            4.0: {
                "opis": "Intencja + strategia + korzyści rozwojowe dla pracownika",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Dodatkowo określa korzyści rozwojowe dla pracownika",
                    "Pokazuje jak zadanie rozwinie kompetencje pracownika"
                ]
            }
        }
    },

    "stan_docelowy": {
        "nazwa": "Określenie stanu docelowego",
        "opis": "Precyzja w definiowaniu rezultatu końcowego zadania",
        "poziomy": {
            0.0: {
                "opis": "Formułuje zadania ogólnie bez określenia stanu docelowego, metod pomiaru ani czasu",
                "zachowania": [
                    "Brak precyzji w opisie rezultatu",
                    "Nie określa co konkretnie ma zostać osiągnięte",
                    "Zadanie sformułowane w sposób niejasny"
                ]
            },
            1.0: {
                "opis": "Definiuje głównie końcowe rezultaty bez wskazania sposobu realizacji",
                "zachowania": [
                    "Określa tylko efekt końcowy",
                    "Brak opisu procesu dojścia do rezultatu",
                    "Minimalna struktura zadania"
                ]
            },
            2.0: {
                "opis": "Precyzyjnie definiuje stan docelowy zdelegowanych zadań",
                "zachowania": [
                    "Jasny opis rezultatu końcowego",
                    "Określa konkretne parametry sukcesu",
                    "Precyzyjne kryteria ukończenia zadania"
                ]
            },
            3.0: {
                "opis": "Stan docelowy + rozróżnienie celów i rezultatów + wpływ pracownika",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Jasno rozróżnia cele i rezultaty zadań",
                    "Określa wpływ pracownika na osiągnięcie rezultatów"
                ]
            },
            4.0: {
                "opis": "Pełna definicja stanu docelowego z metodą pomiaru na poziomie wskaźników, produktów i zachowań",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Definiuje stan docelowy wielowymiarowo",
                    "Komunikuje się w sposób ułatwiający pełne zrozumienie efektów końcowych"
                ]
            }
        }
    },

    "metoda_pomiaru": {
        "nazwa": "Ustalenie metody pomiaru",
        "opis": "Czy określa konkretne wskaźniki, produkty lub zachowania do mierzenia sukcesu",
        "poziomy": {
            0.0: {
                "opis": "Nie określa metody pomiaru rezultatów",
                "zachowania": [
                    "Brak wskaźników sukcesu",
                    "Nie ma kryteriów oceny wykonania",
                    "Niemierzalny rezultat"
                ]
            },
            1.0: {
                "opis": "Minimalna metoda pomiaru, głównie intuicyjna",
                "zachowania": [
                    "Ogólne kryteria sukcesu",
                    "Brak konkretnych wskaźników",
                    "Subiektywna ocena wykonania"
                ]
            },
            2.0: {
                "opis": "Określa metodę pomiaru na podstawie wskaźników lub produktów",
                "zachowania": [
                    "Konkretne wskaźniki sukcesu",
                    "Mierzalne kryteria wykonania",
                    "Jasne parametry oceny"
                ]
            },
            3.0: {
                "opis": "Metoda pomiaru na poziomie wskaźników, produktów i zachowań",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Dodatkowo określa oczekiwane zachowania",
                    "Wielowymiarowa metoda oceny"
                ]
            },
            4.0: {
                "opis": "Pełna metoda pomiaru + dostosowanie do kontekstu i kompetencji pracownika",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Dostosowana do poziomu kompetencji pracownika",
                    "Uwzględnia kontekst biznesowy w metodzie pomiaru"
                ]
            }
        }
    },

    "poziom_odpowiedzialnosci": {
        "nazwa": "Wyznaczenie poziomu odpowiedzialności",
        "opis": "Czy deleguje odpowiedzialność procesową, nie tylko zadania wykonawcze",
        "poziomy": {
            0.0: {
                "opis": "Unika delegowania jakichkolwiek zadań niezależnie od charakteru",
                "zachowania": [
                    "Nie deleguje zadań",
                    "Zatrzymuje wszystkie decyzje przy sobie",
                    "Brak zaufania do zespołu"
                ]
            },
            1.0: {
                "opis": "Myli poziom odpowiedzialności z poziomem uprawnień i decyzyjnością",
                "zachowania": [
                    "Deleguje tylko wykonanie bez odpowiedzialności",
                    "Nie daje uprawnień decyzyjnych",
                    "Pracownik jest tylko wykonawcą"
                ]
            },
            2.0: {
                "opis": "Deleguje zadania o niskim poziomie ryzyka/wpływu na biznes",
                "zachowania": [
                    "Deleguje rutynowe zadania",
                    "Daje ograniczoną odpowiedzialność",
                    "Zachowuje kontrolę nad decyzjami strategicznymi"
                ]
            },
            3.0: {
                "opis": "Deleguje nie tylko zadania ale również odpowiedzialność procesową",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Przekazuje odpowiedzialność za proces",
                    "Daje autonomię w podejmowaniu decyzji"
                ]
            },
            4.0: {
                "opis": "Deleguje odpowiedzialność procesową w zgodzie ze strategią + zadania strategiczne",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Deleguje zadania o strategicznym charakterze",
                    "Odpowiedzialność zgodna ze strategią organizacji",
                    "Zwiększa motywację przez strategiczny charakter zadań"
                ]
            }
        }
    },

    "harmonogram": {
        "nazwa": "Zaplanowanie harmonogramu",
        "opis": "Czy planuje harmonogram w konsultacji z pracownikiem",
        "poziomy": {
            0.0: {
                "opis": "Nie określa czasu realizacji zadania",
                "zachowania": [
                    "Brak ram czasowych",
                    "Nie ustala deadline'ów",
                    "Niejasne oczekiwania czasowe"
                ]
            },
            1.0: {
                "opis": "Planuje harmonogram bez konsultacji z pracownikiem",
                "zachowania": [
                    "Narzuca terminy jednostronnie",
                    "Nie pyta o możliwości pracownika",
                    "Może frustrować zbyt wysokimi oczekiwaniami lub wydłużać czas oddania prac"
                ]
            },
            2.0: {
                "opis": "Planuje harmonogram z uwzględnieniem opinii pracownika",
                "zachowania": [
                    "Konsultuje terminy",
                    "Pyta o dostępność i możliwości",
                    "Wspólnie ustala realistyczny harmonogram"
                ]
            },
            3.0: {
                "opis": "Harmonogram konsultowany + kamienie milowe + elastyczność",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Określa kluczowe punkty kontrolne",
                    "Zostawia przestrzeń na elastyczność"
                ]
            },
            4.0: {
                "opis": "Pełna konsultacja harmonogramu z uwzględnieniem rozwoju kompetencji",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Harmonogram uwzględnia czas na naukę",
                    "Dopasowany do tempa rozwoju pracownika"
                ]
            }
        }
    },

    "monitorowanie": {
        "nazwa": "Określenie procesu monitorowania",
        "opis": "Czy definiuje plan monitorowania przebiegu zadań",
        "poziomy": {
            0.0: {
                "opis": "Nie definiuje planu monitorowania, co przekłada się na niższą motywację",
                "zachowania": [
                    "Brak punktów kontrolnych",
                    "Nie określa momentów sprawdzenia postępów",
                    "Pracownik pozostawiony sam sobie"
                ]
            },
            1.0: {
                "opis": "Minimalny plan monitorowania, głównie na końcu zadania",
                "zachowania": [
                    "Sprawdza tylko efekt końcowy",
                    "Brak monitorowania w trakcie realizacji",
                    "Reaguje dopiero gdy jest problem"
                ]
            },
            2.0: {
                "opis": "Określa proces monitorowania z konkretnymi punktami kontrolnymi",
                "zachowania": [
                    "Ustala momenty kontrolne",
                    "Planuje regularne check-iny",
                    "Jasny plan monitorowania postępów"
                ]
            },
            3.0: {
                "opis": "Plan monitorowania + komunikacja etapowa podczas wdrażania",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Komunikuje się etapowo (nie pomija szczegółów)",
                    "Regularny feedback w trakcie realizacji"
                ]
            },
            4.0: {
                "opis": "Pełny plan monitorowania dostosowany do poziomu autonomii pracownika",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Dostosowuje częstotliwość monitorowania do kompetencji",
                    "Balansuje między wsparciem a autonomią"
                ]
            }
        }
    },

    "sprawdzenie_zrozumienia": {
        "nazwa": "Sprawdzenie zrozumienia przez pracownika",
        "opis": "Czy stosuje pytania otwarte aby sprawdzić jak pracownik rozumie zadanie",
        "poziomy": {
            0.0: {
                "opis": "Nie pyta pracownika o rozumienie rezultatów i procesu realizacji",
                "zachowania": [
                    "Zakłada że pracownik zrozumiał",
                    "Nie weryfikuje zrozumienia",
                    "Brak pytań sprawdzających"
                ]
            },
            1.0: {
                "opis": "Pyta w sposób zamknięty ('Rozumiesz?', 'Jasne?')",
                "zachowania": [
                    "Pytania tak/nie",
                    "Nie weryfikuje głębokości zrozumienia",
                    "Powierzchowne sprawdzenie"
                ]
            },
            2.0: {
                "opis": "Stosuje pytania otwarte o rozumienie zadania",
                "zachowania": [
                    "Pyta 'Jak rozumiesz to zadanie?'",
                    "Weryfikuje zrozumienie celów",
                    "Daje przestrzeń na pytania pracownika"
                ]
            },
            3.0: {
                "opis": "Pytania otwarte o rozumienie procesu wykonania i rezultatów",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Każdorazowo pyta o rozumienie przebiegu prac",
                    "Weryfikuje zrozumienie zarówno celów jak i procesu"
                ]
            },
            4.0: {
                "opis": "Pełna weryfikacja zrozumienia + zachęcanie do pytań i współtworzenia planu",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Zachęca pracowników do opiniowania",
                    "Każdorazowo pyta o pomysły w trakcie planowania",
                    "Współtworzy plan wykonania z pracownikiem"
                ]
            }
        }
    }
}


# ---------------------------------------------------------------------------
# KOMPETENCJA 2: PODEJMOWANIE DECYZJI NA BAZIE KRYTERIÓW (6 wymiarów)
# ---------------------------------------------------------------------------

ALGORYTM_DECYZJE = [
    "1. Zdefiniuj rezultaty i zakres kluczowej decyzji",
    "2. Zmapuj otoczenie i kontekst podejmowanej decyzji",
    "3. Określ i poranguj kryteria decyzyjne",
    "4. Zmapuj ryzyka podejmowanej decyzji",
    "5. Przeanalizuj alternatywne scenariusze planowanej decyzji",
    "6. Podejmij decyzję określając sposób zakomunikowania jej pracownikom"
]

WYMIARY_DECYZJE = {
    "rezultaty_zakres": {
        "nazwa": "Definiowanie rezultatów i zakresu decyzji",
        "opis": "Czy menedżer tworzy listę kluczowych decyzji strategicznych i definiuje ich rezultaty oraz zakres",
        "poziomy": {
            0.0: {
                "opis": "Nie tworzy listy kluczowych decyzji strategicznych, unika określania efektów decyzji",
                "zachowania": [
                    "Nie tworzy listy kluczowych decyzji strategicznych istotnych z punktu widzenia rozwoju obszaru biznesu",
                    "Unika określania efektów podejmowanych przez siebie decyzji",
                    "Nie definiuje zakresu (granic) decyzji jakie ma zamiar podjąć"
                ]
            },
            1.0: {
                "opis": "Definiuje rezultaty decyzji w sposób ogólnikowy, bez precyzyjnego zakresu",
                "zachowania": [
                    "Ogólnikowo określa efekty planowanych decyzji",
                    "Nie precyzuje granic decyzji",
                    "Brak powiązania decyzji z celami strategicznymi"
                ]
            },
            2.0: {
                "opis": "Posiada zdefiniowane rezultaty planowanych decyzji",
                "zachowania": [
                    "Posiada zdefiniowane rezultaty planowanych decyzji",
                    "Określa zakres decyzji którą planuje podjąć",
                    "Łączy decyzję z kontekstem biznesowym"
                ]
            },
            3.0: {
                "opis": "Precyzyjnie definiuje rezultaty i zakres z uwzględnieniem wpływu na strategię",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Powiązuje rezultaty decyzji z celami strategicznymi organizacji",
                    "Jasno komunikuje zakres i granice decyzji interesariuszom"
                ]
            },
            4.0: {
                "opis": "Pełna definicja rezultatów z analizą wpływu na wszystkich interesariuszy",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Analizuje wpływ decyzji na wszystkich interesariuszy",
                    "Zachęca pracowników do opiniowania i wspierania wdrożenia decyzji"
                ]
            }
        }
    },

    "kontekst_otoczenie": {
        "nazwa": "Mapowanie otoczenia i kontekstu decyzji",
        "opis": "Czy menedżer analizuje otoczenie biznesowe i kontekst podczas podejmowania decyzji",
        "poziomy": {
            0.0: {
                "opis": "Nie analizuje otoczenia biznesowego podczas podejmowania decyzji",
                "zachowania": [
                    "Nie precyzuje kontekstu podejmowanych przez siebie decyzji",
                    "Nie analizuje otoczenia biznesowego podczas podejmowanych decyzji",
                    "Ignoruje czynniki zewnętrzne wpływające na decyzję"
                ]
            },
            1.0: {
                "opis": "Sprawdza kontekst decyzji bez uwzględnienia wszystkich istotnych informacji",
                "zachowania": [
                    "Sprawdza kontekst podejmowanych decyzji bez uwzględnienia wszystkich istotnych informacji i/lub danych",
                    "Pomija część kluczowych czynników otoczenia",
                    "Powierzchowna analiza kontekstu"
                ]
            },
            2.0: {
                "opis": "Posiada analizę otoczenia biznesowego podczas podejmowania decyzji",
                "zachowania": [
                    "Posiada analizę otoczenia biznesowego podczas podejmowania przez siebie decyzji",
                    "Uwzględnia kluczowe dane i informacje",
                    "Bierze pod uwagę kontekst rynkowy i organizacyjny"
                ]
            },
            3.0: {
                "opis": "Dogłębna analiza otoczenia z uwzględnieniem trendów i zmian",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Analizuje trendy i zmiany w otoczeniu biznesowym",
                    "Uwzględnia perspektywy różnych interesariuszy"
                ]
            },
            4.0: {
                "opis": "Kompleksowa analiza kontekstu z prognozowaniem zmian otoczenia",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Prognozuje zmiany w otoczeniu i ich wpływ na decyzję",
                    "Każdorazowo pyta pracowników o ich opinie i pomysły w trakcie planowania decyzji"
                ]
            }
        }
    },

    "kryteria_decyzyjne": {
        "nazwa": "Określanie i rangowanie kryteriów decyzyjnych",
        "opis": "Czy menedżer precyzyjnie określa kryteria decyzyjne i nadaje im wagi",
        "poziomy": {
            0.0: {
                "opis": "Kryteria decyzyjne nie są określone, decyzje intuicyjne lub emocjonalne",
                "zachowania": [
                    "Kryteria decyzyjne nie są jednoznacznie określone",
                    "Wiele kryteriów ma charakter intuicyjny i/lub emocjonalny",
                    "Brak systematycznego podejścia do kryteriów"
                ]
            },
            1.0: {
                "opis": "Posiada krótką listę kryteriów bez jasnego rangowania",
                "zachowania": [
                    "Posiada wyłącznie krótką listę opcji oraz założeń decyzyjnych",
                    "Nie różnicuje wagi poszczególnych kryteriów",
                    "Kryteria niespójne lub niekompletne"
                ]
            },
            2.0: {
                "opis": "Precyzyjnie określa różnorodne kryteria decyzyjne",
                "zachowania": [
                    "Precyzyjnie określa różnorodne kryteria decyzyjne",
                    "Określa wagi poszczególnych kryteriów na podejmowane przez siebie decyzje",
                    "Kryteria oparte na danych i faktach"
                ]
            },
            3.0: {
                "opis": "Kryteria z wagami + systematyczna metoda oceny opcji",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Stosuje systematyczną metodę oceny opcji według kryteriów",
                    "Weryfikuje kryteria z interesariuszami"
                ]
            },
            4.0: {
                "opis": "Zaawansowany system kryteriów dostosowany do kontekstu z zaangażowaniem zespołu",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Zachęca pracowników do opiniowania kryteriów",
                    "Dostosowuje kryteria do zmiennego kontekstu biznesowego"
                ]
            }
        }
    },

    "mapowanie_ryzyk": {
        "nazwa": "Mapowanie ryzyk podejmowanej decyzji",
        "opis": "Czy menedżer identyfikuje i analizuje ryzyka związane z decyzją przed jej podjęciem",
        "poziomy": {
            0.0: {
                "opis": "Nie mapuje ryzyk decyzji, ignoruje potencjalne zagrożenia",
                "zachowania": [
                    "Nie analizuje ryzyk przed podjęciem decyzji",
                    "Ignoruje potencjalne konsekwencje negatywne",
                    "Brak świadomości zagrożeń"
                ]
            },
            1.0: {
                "opis": "Mapuje ryzyka dopiero na etapie komunikowania decyzji do zespołu",
                "zachowania": [
                    "Mapuje ryzyka dopiero na etapie komunikowania decyzji do zespołu",
                    "Reaktywne podejście do ryzyk",
                    "Analiza ryzyk po fakcie"
                ]
            },
            2.0: {
                "opis": "Identyfikuje kluczowe ryzyka przed podjęciem decyzji",
                "zachowania": [
                    "Identyfikuje główne ryzyka przed decyzją",
                    "Przygotowuje podstawowy plan mitygacji",
                    "Dostosowuje decyzje do zmapowanych wcześniej ryzyk"
                ]
            },
            3.0: {
                "opis": "Systematyczna analiza ryzyk z planem mitygacji i monitoringu",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Systematycznie analizuje ryzyka na wielu poziomach",
                    "Opracowuje plan monitorowania i reagowania na ryzyka"
                ]
            },
            4.0: {
                "opis": "Proaktywne zarządzanie ryzykiem z angażowaniem zespołu w identyfikację zagrożeń",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Angażuje zespół w identyfikację i ocenę ryzyk",
                    "Tworzy scenariusze reakcji na zmaterializowane ryzyka"
                ]
            }
        }
    },

    "alternatywne_scenariusze": {
        "nazwa": "Analiza alternatywnych scenariuszy",
        "opis": "Czy menedżer analizuje alternatywne scenariusze i opcje decyzyjne",
        "poziomy": {
            0.0: {
                "opis": "Nie analizuje alternatywnych scenariuszy, jedno rozwiązanie",
                "zachowania": [
                    "Nie rozważa alternatywnych opcji decyzyjnych",
                    "Trzyma się jednego scenariusza bez refleksji",
                    "Brak analizy wariantowej"
                ]
            },
            1.0: {
                "opis": "Posiada krótką listę opcji bez pogłębionej analizy",
                "zachowania": [
                    "Posiada wyłącznie krótką listę opcji oraz założeń decyzyjnych",
                    "Nie analizuje możliwych opcji decyzyjnych trzymając się raz ustalonych kryteriów",
                    "Powierzchowna analiza alternatyw"
                ]
            },
            2.0: {
                "opis": "Analizuje kilka opcji decyzyjnych z ich konsekwencjami",
                "zachowania": [
                    "Rozważa kilka alternatywnych opcji",
                    "Analizuje konsekwencje każdej opcji",
                    "Porównuje opcje według ustalonych kryteriów"
                ]
            },
            3.0: {
                "opis": "Posiada kilka alternatywnych scenariuszy z dostosowanymi opcjami",
                "zachowania": [
                    "Posiada kilka alternatywnych scenariuszy przyszłych wydarzeń",
                    "Dostosowuje opcje decyzji do różnych scenariuszy",
                    "Przygotowuje plany awaryjne"
                ]
            },
            4.0: {
                "opis": "Kompleksowa analiza scenariuszy z zaangażowaniem zespołu i elastycznością",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Angażuje zespół w tworzenie scenariuszy",
                    "Buduje elastyczne strategie pozwalające na szybką zmianę kursu"
                ]
            }
        }
    },

    "komunikacja_decyzji": {
        "nazwa": "Komunikowanie i wdrażanie decyzji",
        "opis": "Czy menedżer skutecznie komunikuje decyzję i jej strategiczne znaczenie pracownikom",
        "poziomy": {
            0.0: {
                "opis": "Nie komunikuje decyzji lub komunikuje bez uzasadnienia",
                "zachowania": [
                    "Nie informuje zespołu o podjętych decyzjach",
                    "Brak wyjaśnienia powodów decyzji",
                    "Decyzje wdrażane bez komunikacji"
                ]
            },
            1.0: {
                "opis": "Komunikuje decyzje bez podania ich strategicznego znaczenia",
                "zachowania": [
                    "Komunikuje swoje decyzje bez podania ich strategicznego znaczenia",
                    "Nie komunikuje z jakich powodów należy podjąć działania",
                    "Brak kontekstu przy komunikacji decyzji"
                ]
            },
            2.0: {
                "opis": "Komunikuje decyzje z podstawowym uzasadnieniem",
                "zachowania": [
                    "Wyjaśnia podstawowe powody decyzji",
                    "Komunikuje oczekiwane działania",
                    "Informuje o konsekwencjach decyzji dla zespołu"
                ]
            },
            3.0: {
                "opis": "Komunikuje się etapowo, nie pomija szczegółów przy wdrażaniu zmian",
                "zachowania": [
                    "Komunikuje się etapowo (nie pomija szczegółów) podczas wdrażania zmian",
                    "Wyjaśnia strategiczne znaczenie decyzji",
                    "Angażuje zespół we wdrożenie"
                ]
            },
            4.0: {
                "opis": "Pełna komunikacja z angażowaniem pracowników w planowanie i wdrożenie",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Każdorazowo pyta pracowników o ich opinie i pomysły w trakcie planowania decyzji oraz ich wdrożenia",
                    "Buduje zaangażowanie i współodpowiedzialność za decyzję"
                ]
            }
        }
    }
}


# ---------------------------------------------------------------------------
# KOMPETENCJA 3: OKREŚLANIE CELÓW I PRIORYTETÓW (6 wymiarów)
# ---------------------------------------------------------------------------

ALGORYTM_PRIORYTETY = [
    "1. Zdefiniuj główne cele i priorytety",
    "2. Określ kontekst podejmowania decyzji",
    "3. Wybierz optymalny tryb decyzji",
    "4. Wybierz i poranguj kryteria priorytetyzacji",
    "5. Przeanalizuj możliwe opcje i wybierz metodę podjęcia decyzji",
    "6. Podejmij decyzję i skaskaduj, wyjaśniając pracownikom kryteria priorytetyzacji"
]

WYMIARY_PRIORYTETY = {
    "cele_priorytety": {
        "nazwa": "Definiowanie głównych celów i priorytetów",
        "opis": "Czy menedżer jasno definiuje cele i priorytety oraz rozróżnia siłę wpływu decyzji na biznes",
        "poziomy": {
            0.0: {
                "opis": "Unika podejmowania decyzji i/lub je przeciąga, nie definiuje celów",
                "zachowania": [
                    "Unika podejmowania decyzji i/lub je przeciąga",
                    "Nie definiuje priorytetów dla zespołu",
                    "Brak jasnych celów biznesowych"
                ]
            },
            1.0: {
                "opis": "Zmienia priorytety na bazie szczątkowych informacji lub emocji",
                "zachowania": [
                    "Zmienia priorytety na bazie szczątkowych informacji bądź emocji własnych i/lub współpracowników",
                    "Niestabilne priorytety powodujące chaos w zespole",
                    "Brak systematycznego podejścia do celów"
                ]
            },
            2.0: {
                "opis": "W krótkim czasie podejmuje decyzje o niskim wpływie, rozróżnia siłę wpływu",
                "zachowania": [
                    "W krótkim czasie podejmuje decyzje o niskim poziomie wpływu na biznes",
                    "Rozróżnia siłę wpływu decyzji na efekty biznesowe",
                    "Deleguje na pracowników decyzje o niższym poziomie ryzyka i/lub wpływu na biznes"
                ]
            },
            3.0: {
                "opis": "Systematycznie definiuje cele strategiczne i operacyjne z priorytetami",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Definiuje cele strategiczne i operacyjne",
                    "Jasno komunikuje hierarchię priorytetów"
                ]
            },
            4.0: {
                "opis": "Zaawansowane zarządzanie celami z kaskadowaniem na zespół",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Kaskaduje cele na poszczególnych pracowników",
                    "Buduje odpowiedzialność zespołu za realizację celów"
                ]
            }
        }
    },

    "kontekst_decyzji": {
        "nazwa": "Określanie kontekstu podejmowania decyzji",
        "opis": "Czy menedżer analizuje kontekst i definiuje zmienne wpływające na decyzję",
        "poziomy": {
            0.0: {
                "opis": "Nie definiuje kontekstu podejmowanych decyzji",
                "zachowania": [
                    "Nie definiuje kontekstu podejmowanych decyzji",
                    "Ignoruje zmienne wpływające na sytuację",
                    "Decyzje oderwane od realiów"
                ]
            },
            1.0: {
                "opis": "Ustala jeden schemat decyzyjny dla różnych kontekstów bez analizy",
                "zachowania": [
                    "Ustala jeden schemat decyzyjny dla różnych kontekstów bez analizy dodatkowych zmiennych",
                    "Nie dostosowuje podejścia do sytuacji",
                    "Sztywny schemat niezależnie od okoliczności"
                ]
            },
            2.0: {
                "opis": "Analizuje kontekst i dostosowuje podejście do sytuacji",
                "zachowania": [
                    "Identyfikuje kluczowe zmienne kontekstualne",
                    "Dostosowuje podejście do specyfiki sytuacji",
                    "Uwzględnia informacje od zespołu"
                ]
            },
            3.0: {
                "opis": "Dogłębna analiza kontekstu z uwzględnieniem wielu perspektyw",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Uwzględnia perspektywy różnych interesariuszy",
                    "Analizuje kontekst wielowymiarowo"
                ]
            },
            4.0: {
                "opis": "Kompleksowa analiza kontekstu z prognozowaniem i adaptacją",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Prognozuje zmiany kontekstualne i ich wpływ",
                    "Elastycznie adaptuje podejście do zmieniających się warunków"
                ]
            }
        }
    },

    "tryb_decyzji": {
        "nazwa": "Wybór optymalnego trybu decyzji",
        "opis": "Czy menedżer świadomie wybiera tryb podejmowania decyzji (samodzielny vs zespołowy)",
        "poziomy": {
            0.0: {
                "opis": "Nie rozróżnia trybów podejmowania decyzji",
                "zachowania": [
                    "Nie ma świadomości różnych trybów decyzyjnych",
                    "Podejmuje decyzje chaotycznie",
                    "Brak refleksji nad sposobem podejmowania decyzji"
                ]
            },
            1.0: {
                "opis": "Korzysta głównie z trybu samodzielnego niezależnie od kontekstu",
                "zachowania": [
                    "Korzysta głównie z trybu samodzielnego podejmowania decyzji niezależnie od kontekstu oraz konsekwencji",
                    "Nie angażuje zespołu w proces decyzyjny",
                    "Nie dostosowuje trybu do sytuacji"
                ]
            },
            2.0: {
                "opis": "Korzysta z trybu zespołowego gdy istotne jest doskonalenie kompetencji",
                "zachowania": [
                    "Korzysta z trybu podejmowania decyzji wraz z zespołem jeśli istotne jest doskonalenie samodzielności i/lub kompetencji pracowników",
                    "Rozróżnia sytuacje wymagające różnych trybów",
                    "Deleguje na pracowników decyzje o niższym poziomie ryzyka"
                ]
            },
            3.0: {
                "opis": "Świadomie wybiera tryb decyzji uwzględniając wpływ na efektywność wdrożenia",
                "zachowania": [
                    "Wybierając tryb podejmowania decyzji uwzględnia jej wpływ na efektywność wdrożenia zmian biznesowych",
                    "Balansuje między szybkością a jakością decyzji",
                    "Angażuje odpowiednie osoby w proces decyzyjny"
                ]
            },
            4.0: {
                "opis": "Zaawansowane zarządzanie trybami z budowaniem kultury decyzyjności",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Buduje kulturę podejmowania decyzji w zespole",
                    "Rozwija autonomię decyzyjną pracowników"
                ]
            }
        }
    },

    "kryteria_priorytetyzacji": {
        "nazwa": "Wybór i rangowanie kryteriów priorytetyzacji",
        "opis": "Czy menedżer posiada standardowy zestaw kryteriów i adekwatnie je modyfikuje",
        "poziomy": {
            0.0: {
                "opis": "Brak kryteriów priorytetyzacji, chaotyczne ustalanie priorytetów",
                "zachowania": [
                    "Nie posiada kryteriów priorytetyzacji",
                    "Priorytety ustalane ad hoc bez systemu",
                    "Brak powtarzalnego procesu"
                ]
            },
            1.0: {
                "opis": "Dokłada kolejne kryteria co utrudnia/wydłuża podjęcie decyzji",
                "zachowania": [
                    "Pomimo jasnych wytycznych organizacyjnych dokłada kolejne kryteria decyzyjne co utrudnia i/lub wydłuża podjęcie decyzji",
                    "Nadmiar kryteriów paraliżuje proces",
                    "Brak hierarchii kryteriów"
                ]
            },
            2.0: {
                "opis": "Posiada standardowy zestaw kryteriów, adekwatnie modyfikuje do potrzeb",
                "zachowania": [
                    "Posiada standardowy zestaw kryteriów dla danych procesów i/lub zadań które adekwatnie do potrzeb modyfikuje",
                    "Komunikuje kryteria priorytetyzacji zadań pracownikom",
                    "Kryteria jasne i zrozumiałe"
                ]
            },
            3.0: {
                "opis": "Systematyczne rangowanie kryteriów z uwzględnieniem strategii",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Ranguje kryteria według wpływu strategicznego",
                    "Regularnie weryfikuje i aktualizuje kryteria"
                ]
            },
            4.0: {
                "opis": "Zaawansowany system kryteriów z zaangażowaniem zespołu i ciągłym doskonaleniem",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Angażuje zespół w definiowanie kryteriów",
                    "Systematycznie doskonali proces priorytetyzacji"
                ]
            }
        }
    },

    "opcje_metody": {
        "nazwa": "Analiza opcji i wybór metody decyzji",
        "opis": "Czy menedżer posiada metody oceny możliwych opcji decyzyjnych",
        "poziomy": {
            0.0: {
                "opis": "Nie analizuje opcji decyzyjnych, brak metody",
                "zachowania": [
                    "Nie analizuje możliwych opcji decyzyjnych",
                    "Brak systematycznej metody podejmowania decyzji",
                    "Decyzje podejmowane bez analizy"
                ]
            },
            1.0: {
                "opis": "Nie analizuje opcji, trzyma się raz ustalonych kryteriów",
                "zachowania": [
                    "Nie analizuje możliwych opcji decyzyjnych trzymając się raz ustalonych kryteriów",
                    "Brak elastyczności w podejściu",
                    "Ignoruje nowe informacje"
                ]
            },
            2.0: {
                "opis": "Posiada metody oceny opcji decyzyjnych",
                "zachowania": [
                    "Posiada metody oceny możliwych opcji decyzyjnych podczas podejmowania decyzji oraz priorytetyzacji zadań",
                    "Porównuje opcje według kryteriów",
                    "Wybiera opcję na podstawie analizy"
                ]
            },
            3.0: {
                "opis": "Zaawansowane metody oceny z analizą wpływu na wdrożenie zmian",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Wybierając metodę uwzględnia wpływ na efektywność wdrożenia zmian biznesowych",
                    "Stosuje wielokryterialne metody oceny"
                ]
            },
            4.0: {
                "opis": "Kompleksowe metody z ciągłym doskonaleniem i uczeniem się z doświadczeń",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Systematycznie doskonali metody decyzyjne",
                    "Uczy się z wcześniejszych decyzji i ich efektów"
                ]
            }
        }
    },

    "kaskadowanie": {
        "nazwa": "Kaskadowanie decyzji i komunikacja kryteriów",
        "opis": "Czy menedżer skutecznie kaskaduje decyzje wyjaśniając pracownikom kryteria priorytetyzacji",
        "poziomy": {
            0.0: {
                "opis": "Nie komunikuje priorytetów ani kryteriów decyzyjnych zespołowi",
                "zachowania": [
                    "Nie komunikuje z jakich powodów należy podjąć działania w zakresie zmian priorytetów zadaniowych",
                    "Zespół nie zna priorytetów",
                    "Brak kaskadowania decyzji"
                ]
            },
            1.0: {
                "opis": "Komunikuje decyzje bez wyjaśnienia kryteriów priorytetyzacji",
                "zachowania": [
                    "Informuje o decyzjach bez uzasadnienia",
                    "Nie wyjaśnia kryteriów stojących za priorytetami",
                    "Komunikacja jednostronna"
                ]
            },
            2.0: {
                "opis": "Komunikuje kryteria priorytetyzacji zadań pracownikom",
                "zachowania": [
                    "Komunikuje kryteria priorytetyzacji zadań pracownikom",
                    "Wyjaśnia powody zmian priorytetów",
                    "Zapewnia zrozumienie priorytetów przez zespół"
                ]
            },
            3.0: {
                "opis": "Systematyczne kaskadowanie z angażowaniem pracowników",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Angażuje pracowników w ustalanie priorytetów operacyjnych",
                    "Weryfikuje zrozumienie priorytetów przez zespół"
                ]
            },
            4.0: {
                "opis": "Pełne kaskadowanie z budowaniem współodpowiedzialności",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Buduje współodpowiedzialność za priorytety",
                    "Pracownicy samodzielnie stosują kryteria priorytetyzacji"
                ]
            }
        }
    }
}


# ---------------------------------------------------------------------------
# KOMPETENCJA 4: UDZIELANIE INFORMACJI ZWROTNEJ (5 wymiarów)
# ---------------------------------------------------------------------------

ALGORYTM_FEEDBACK = [
    "1. Przedstaw fakty / zachowania pracownika",
    "2. Określ swoje emocje względem zachowań pracownika",
    "3. Podaj konsekwencje zachowań pracownika",
    "4. Przekaż swoje oczekiwania względem pracownika",
    "5. Sprawdź jak pracownik zrozumiał informację zwrotną"
]

WYMIARY_FEEDBACK = {
    "fakty_zachowania": {
        "nazwa": "Przedstawianie faktów i zachowań pracownika",
        "opis": "Czy menedżer precyzyjnie opisuje konkretne zachowania pracownika oparte na faktach",
        "poziomy": {
            0.0: {
                "opis": "Stosuje ogólniki i abstrakcje zamiast konkretnych faktów",
                "zachowania": [
                    "Stosuje informacje zwrotne które bazują na ogólnikach i mogą silnie zdemotywować pracownika ('nigdy nie robisz nic na czas')",
                    "Formułuje informacje na wysokim poziomie abstrakcji trudne dla pracownika w interpretacji ('nie zachowuj się jak przedszkolak')",
                    "Brak odniesienia do konkretnych zachowań"
                ]
            },
            1.0: {
                "opis": "Częściowo opisuje zachowania ale z dużą dozą ogólników",
                "zachowania": [
                    "Miesza fakty z opiniami i interpretacjami",
                    "Nie korzysta regularnie z informacji zwrotnej, stosuje ją głównie podczas formalnych ocen okresowych lub publicznych wystąpień",
                    "Opisy zachowań nieprecyzyjne"
                ]
            },
            2.0: {
                "opis": "Potrafi precyzyjnie zdefiniować skuteczne i nieskuteczne zachowania",
                "zachowania": [
                    "Potrafi precyzyjnie zdefiniować skuteczne i/lub nieskuteczne zachowania pracownika",
                    "Oddziela fakty od interpretacji",
                    "Opisuje konkretne sytuacje i zachowania"
                ]
            },
            3.0: {
                "opis": "Precyzyjne fakty + prowadzenie rozmowy głównie poprzez pytania",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Potrafi prowadzić informację zwrotną korzystając głównie z pytań",
                    "Angażuje pracownika w refleksję nad zachowaniami"
                ]
            },
            4.0: {
                "opis": "Mistrzowskie opisywanie zachowań z dostosowaniem do kompetencji pracownika",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Komunikuje się w sposób który opisuje jasno zachowania oraz rezultaty które mają zostać osiągnięte poprzez ich zmianę",
                    "Dostosowuje sposób udzielania informacji zwrotnej do kompetencji pracownika"
                ]
            }
        }
    },

    "emocje": {
        "nazwa": "Określanie emocji względem zachowań pracownika",
        "opis": "Czy menedżer komunikuje swoje emocje w sposób konstruktywny bez podważania poczucia skuteczności",
        "poziomy": {
            0.0: {
                "opis": "Używa słów budzących negatywne emocje, podważa poczucie skuteczności",
                "zachowania": [
                    "Informacje przekazuje słowami które budzą negatywne emocje i podważają poczucie skuteczności pracownika (np. błąd, porażka)",
                    "Komunikacja emocjonalna destrukcyjna",
                    "Atakuje osobę zamiast zachowań"
                ]
            },
            1.0: {
                "opis": "Nadmiernie skupia się na emocjach utrudniając zrozumienie oczekiwań",
                "zachowania": [
                    "Nadmiernie skupia się na emocjach w przekazie co utrudnia pracownikowi zrozumienie oczekiwań oraz frustruje pracownika",
                    "Emocje dominują nad przekazem merytorycznym",
                    "Brak równowagi między emocjami a faktami"
                ]
            },
            2.0: {
                "opis": "Komunikuje emocje w sposób zrównoważony bez podważania pracownika",
                "zachowania": [
                    "Komunikuje swoje emocje bez podważania wartości pracownika",
                    "Używa konstruktywnego języka emocji",
                    "Zachowuje równowagę między emocjami a faktami"
                ]
            },
            3.0: {
                "opis": "Emocje jako element konstruktywnej rozmowy wzmacniający przekaz",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Wykorzystuje emocje jako element wzmacniający przekaz",
                    "Tworzy bezpieczną przestrzeń do rozmowy"
                ]
            },
            4.0: {
                "opis": "Mistrzowska komunikacja emocji budująca relację i zaufanie",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Emocje budują relację i zaufanie",
                    "Dostosowuje komunikację emocji do osobowości pracownika"
                ]
            }
        }
    },

    "konsekwencje": {
        "nazwa": "Podawanie konsekwencji zachowań pracownika",
        "opis": "Czy menedżer wskazuje i wyjaśnia następstwa zachowań zarówno skutecznych jak i nieskutecznych",
        "poziomy": {
            0.0: {
                "opis": "Nie podaje konsekwencji zachowań pracownika",
                "zachowania": [
                    "Nie wyjaśnia jakie są następstwa zachowań pracownika",
                    "Pracownik nie rozumie wpływu swoich zachowań",
                    "Brak informacji o konsekwencjach"
                ]
            },
            1.0: {
                "opis": "Podaje konsekwencje tylko zachowań do skorygowania",
                "zachowania": [
                    "Podaje konsekwencje ale z reguły tylko tych zachowań które należy skorygować",
                    "Brak informacji o pozytywnych następstwach",
                    "Jednostronne skupienie na negatywach"
                ]
            },
            2.0: {
                "opis": "Wskazuje konsekwencje zarówno pozytywnych jak i negatywnych zachowań",
                "zachowania": [
                    "Podaje konsekwencje zachowań skutecznych i nieskutecznych",
                    "Wyjaśnia wpływ zachowań na wyniki",
                    "Równowaga korygującej i wzmacniającej informacji"
                ]
            },
            3.0: {
                "opis": "Każdorazowo wskazuje i wyjaśnia następstwa zachowań obu typów",
                "zachowania": [
                    "Każdorazowo wskazuje i wyjaśnia następstwa zachowań zarówno nieskutecznych jak i skutecznych",
                    "Łączy konsekwencje z celami zespołu/organizacji",
                    "Pokazuje długoterminowe następstwa zachowań"
                ]
            },
            4.0: {
                "opis": "Kompleksowe wyjaśnianie konsekwencji z angażowaniem pracownika w refleksję",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Angażuje pracownika w samodzielne odkrywanie konsekwencji",
                    "Buduje świadomość wpływu zachowań na otoczenie"
                ]
            }
        }
    },

    "oczekiwania": {
        "nazwa": "Przekazywanie oczekiwań względem pracownika",
        "opis": "Czy menedżer jasno określa jak pracownik powinien działać po otrzymaniu informacji zwrotnej",
        "poziomy": {
            0.0: {
                "opis": "Nie przekazuje oczekiwań co do przyszłych zachowań",
                "zachowania": [
                    "Nie mówi pracownikowi co powinien zmienić",
                    "Brak jasnych oczekiwań po feedbacku",
                    "Pracownik nie wie jak działać dalej"
                ]
            },
            1.0: {
                "opis": "Oczekiwania ogólnikowe, trudne do przełożenia na działanie",
                "zachowania": [
                    "Formułuje oczekiwania w sposób ogólny",
                    "Pracownik ma trudność z interpretacją oczekiwań",
                    "Brak konkretnych wskazówek"
                ]
            },
            2.0: {
                "opis": "Określa jak pracownik powinien działać od momentu otrzymania feedbacku",
                "zachowania": [
                    "Określa jak pracownik powinien działać od momentu otrzymania informacji zwrotnej w porównaniu do zachowań względem których otrzymał informację zwrotną",
                    "Konkretne i mierzalne oczekiwania",
                    "Jasny plan zmiany zachowań"
                ]
            },
            3.0: {
                "opis": "Precyzyjne oczekiwania z opisem pożądanych rezultatów i zachowań",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Opisuje jasno zachowania oraz rezultaty które mają zostać osiągnięte poprzez zmianę",
                    "Wspiera pracownika w planowaniu rozwoju"
                ]
            },
            4.0: {
                "opis": "Oczekiwania dopasowane do kompetencji pracownika z planem rozwoju",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Dostosowuje oczekiwania do poziomu kompetencji pracownika",
                    "Współtworzy z pracownikiem plan osiągnięcia oczekiwań"
                ]
            }
        }
    },

    "sprawdzenie_zrozumienia_fb": {
        "nazwa": "Sprawdzenie zrozumienia informacji zwrotnej",
        "opis": "Czy menedżer weryfikuje jak pracownik zrozumiał przekazaną informację zwrotną",
        "poziomy": {
            0.0: {
                "opis": "Nie weryfikuje czy pracownik zrozumiał informację zwrotną",
                "zachowania": [
                    "Zakłada że pracownik zrozumiał feedback",
                    "Nie sprawdza zrozumienia",
                    "Brak pytań weryfikujących"
                ]
            },
            1.0: {
                "opis": "Powierzchowne sprawdzenie ('Rozumiesz?', 'OK?')",
                "zachowania": [
                    "Pyta zamknięte pytania weryfikujące",
                    "Nie daje przestrzeni na reakcję pracownika",
                    "Formalne sprawdzenie bez głębi"
                ]
            },
            2.0: {
                "opis": "Stosuje pytania otwarte aby sprawdzić zrozumienie feedbacku",
                "zachowania": [
                    "Pyta pracownika otwartymi pytaniami o zrozumienie",
                    "Daje przestrzeń na pytania i wątpliwości",
                    "Weryfikuje zrozumienie kluczowych punktów"
                ]
            },
            3.0: {
                "opis": "Dogłębna weryfikacja zrozumienia z planem dalszych kroków",
                "zachowania": [
                    "Wszystko z poziomu 2.0",
                    "Prosi pracownika o powtórzenie kluczowych ustaleń",
                    "Wspólnie ustala plan dalszych kroków"
                ]
            },
            4.0: {
                "opis": "Pełna weryfikacja + follow-up i monitoring zmiany zachowań",
                "zachowania": [
                    "Wszystko z poziomu 3.0",
                    "Planuje follow-up spotkania",
                    "Monitoruje zmianę zachowań i daje dodatkowy feedback"
                ]
            }
        }
    }
}


# ---------------------------------------------------------------------------
# ŁADOWANIE DEFINICJI Z JSON (z fallbackiem na hardkodowane stałe)
# ---------------------------------------------------------------------------

_HARDCODED_FALLBACK = {
    "delegowanie": {
        "nazwa": "Formułowanie celów i rezultatów - Delegowanie",
        "wymiary": WYMIARY_DELEGOWANIE,
        "algorytm": ALGORYTM_DELEGOWANIE,
    },
    "podejmowanie_decyzji": {
        "nazwa": "Podejmowanie decyzji na bazie kryteriów",
        "wymiary": WYMIARY_DECYZJE,
        "algorytm": ALGORYTM_DECYZJE,
    },
    "okreslanie_priorytetow": {
        "nazwa": "Określanie celów i priorytetów",
        "wymiary": WYMIARY_PRIORYTETY,
        "algorytm": ALGORYTM_PRIORYTETY,
    },
    "udzielanie_feedbacku": {
        "nazwa": "Udzielanie informacji zwrotnej",
        "wymiary": WYMIARY_FEEDBACK,
        "algorytm": ALGORYTM_FEEDBACK,
    },
}


def _convert_json_poziomy(wymiary_json: dict) -> dict:
    """Konwertuje klucze poziomów z stringów ("0.0") na floaty (0.0)."""
    result = {}
    for key, wym in wymiary_json.items():
        converted = {
            "nazwa": wym["nazwa"],
            "opis": wym["opis"],
            "poziomy": {float(lvl): data for lvl, data in wym["poziomy"].items()},
        }
        result[key] = converted
    return result


def _load_competency_json(comp_id: str) -> dict | None:
    """Ładuje definicję kompetencji z pliku JSON. Zwraca None jeśli brak."""
    path = COMPETENCIES_DIR / f"{comp_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "nazwa": data["nazwa"],
        "wymiary": _convert_json_poziomy(data["wymiary"]),
        "algorytm": data["algorytm"],
        "_version": data.get("version", "1.0"),
        "_source": data.get("source", ""),
    }


def _load_registry() -> dict:
    """Ładuje rejestr kompetencji: z JSON jeśli istnieje, fallback na hardkod."""
    registry = {}
    for comp_id in ["delegowanie", "podejmowanie_decyzji", "okreslanie_priorytetow", "udzielanie_feedbacku"]:
        loaded = _load_competency_json(comp_id)
        if loaded:
            registry[comp_id] = loaded
        else:
            registry[comp_id] = _HARDCODED_FALLBACK[comp_id]
    return registry


def reload_competency_registry():
    """Przeładowuje rejestr kompetencji z plików JSON (wywoływane po edycji)."""
    global COMPETENCY_REGISTRY
    COMPETENCY_REGISTRY = _load_registry()


def save_competency_definition(comp_id: str, data: dict) -> dict:
    """Zapisuje definicję kompetencji do pliku JSON i przeładowuje rejestr."""
    COMPETENCIES_DIR.mkdir(parents=True, exist_ok=True)
    path = COMPETENCIES_DIR / f"{comp_id}.json"
    
    save_data = {
        "id": comp_id,
        "nazwa": data["nazwa"],
        "version": data.get("_version", data.get("version", "1.0")),
        "source": data.get("_source", data.get("source", "4 LEM.pdf")),
        "algorytm": data["algorytm"],
        "wymiary": {},
    }
    for key, wym in data["wymiary"].items():
        save_data["wymiary"][key] = {
            "nazwa": wym["nazwa"],
            "opis": wym["opis"],
            "poziomy": {
                str(lvl): {"opis": p["opis"], "zachowania": p["zachowania"]}
                for lvl, p in wym["poziomy"].items()
            },
        }
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    
    reload_competency_registry()
    return {"competency": comp_id, "saved": True, "path": str(path)}


COMPETENCY_REGISTRY = _load_registry()

COMPETENCY_ALIASES = {
    "decyzje": "podejmowanie_decyzji",
    "priorytety": "okreslanie_priorytetow",
    "feedback": "udzielanie_feedbacku",
}

COMPETENCY_SHORT_NAMES = {v: k for k, v in COMPETENCY_ALIASES.items()}
COMPETENCY_SHORT_NAMES["delegowanie"] = "delegowanie"


def resolve_competency(competency: str) -> str:
    """Tłumaczy alias (np. 'decyzje') na pełną nazwę backendu ('podejmowanie_decyzji').
    Jeśli już pełna — zwraca bez zmian."""
    return COMPETENCY_ALIASES.get(competency, competency)


def competency_short_name(competency: str) -> str:
    """Zwraca krótki ID kompetencji (używany przez frontend)."""
    return COMPETENCY_SHORT_NAMES.get(competency, competency)


def get_available_competencies() -> list[str]:
    """Zwraca listę dostępnych kompetencji."""
    return list(COMPETENCY_REGISTRY.keys())


def get_competency_info(competency: str) -> dict:
    """Zwraca pełne info o kompetencji (nazwa, wymiary, algorytm)."""
    competency = resolve_competency(competency)
    if competency not in COMPETENCY_REGISTRY:
        raise ValueError(f"Nieznana kompetencja: {competency}. Dostępne: {get_available_competencies()}")
    return COMPETENCY_REGISTRY[competency]


def get_wymiary_for_competency(competency: str) -> dict:
    """Zwraca słownik wymiarów dla danej kompetencji."""
    return get_competency_info(competency)["wymiary"]


def get_algorytm_for_competency(competency: str) -> list:
    """Zwraca algorytm (listę kroków) dla danej kompetencji."""
    return get_competency_info(competency)["algorytm"]


def get_poziom_kompetencji(score: float) -> PoziomKompetencji:
    """Mapuje wynik liczbowy 0-4 na poziom kompetencji."""
    if score < 1.0:
        return PoziomKompetencji.NIEEFEKTYWNY
    elif score < 2.0:
        return PoziomKompetencji.BAZOWY
    elif score < 3.0:
        return PoziomKompetencji.EFEKTYWNY
    else:
        return PoziomKompetencji.BIEGLY


def get_wymiar_opis(wymiar: str, score: float, competency: str = "delegowanie") -> str:
    """Zwraca opis poziomu dla danego wymiaru i wyniku."""
    wymiary = get_wymiary_for_competency(competency)
    if wymiar not in wymiary:
        return ""
    score_scaled = score * 4
    poziomy = wymiary[wymiar]["poziomy"]
    closest_level = min(poziomy.keys(), key=lambda x: abs(x - score_scaled))
    return poziomy[closest_level]["opis"]


CASE_CONTEXT = """
Kontekst biznesowy:
Jesteś menedżerem zespołu w bankowości korporacyjnej.
Twój zespół prowadzi kilka równoległych projektów z kluczowymi klientami.
Centrala wyznaczyła nowe priorytety kwartalne:
- wzrost przychodów z segmentu detalicznego
- poprawa omnichanelowej jakości obsługi klientów
- skrócenie czasu decyzyjnego w procesach

Masz ograniczone zasoby zespołu.
Jeden z doświadczonych pracowników jest przeciążony, 
a młodszy pracownik ma potencjał, ale brak mu jeszcze pewności i struktury działania.
"""

CASE_DELEGOWANIE_CONTEXT = CASE_CONTEXT + """
Zadanie:
Opisz jak przeprowadzasz rozmowę delegującą z pracownikiem w sytuacji 
wcześniej ustalonych priorytetów biznesowych. Uwzględnij:
- przygotowanie do rozmowy
- przebieg rozmowy krok po kroku
- sposób podejmowania decyzji co i jak delegować
- planowane efekty rozmowy delegującej
"""
