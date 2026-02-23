# Infrastruktura i konfiguracja produkcyjna LEM

## Schemat infrastruktury

```
                        INTERNET
                           │
              https://lem.digitalunity.pl
                           │
                    ┌──────┴──────┐
                    │  DNS (A)    │
                    │  home.pl    │
                    │ lem → IP    │
                    └──────┬──────┘
                           │
         ┌─────────────────┴─────────────────┐
         │     SERWER HETZNER                │
         │     IP publiczne: 144.76.2.68     │
         │     IP Tailscale: 100.122.147.29  │
         │     Ubuntu 22.04 (Jammy)          │
         │     User: kochnik                 │
         │                                   │
         │  ┌─────────────────────────────┐  │
         │  │  Nginx (reverse proxy)      │  │
         │  │  :443 (HTTPS) + :80 (redir) │  │
         │  │  SSL: Let's Encrypt         │  │
         │  └──────────┬──────────────────┘  │
         │             │ proxy_pass           │
         │             ▼                      │
         │  ┌─────────────────────────────┐  │
         │  │  Gunicorn + Uvicorn         │  │
         │  │  :8010 (localhost)           │  │
         │  │  app.main:app (FastAPI)      │  │
         │  └──────────┬──────────────────┘  │
         │             │ HTTP API             │
         │             ▼                      │
         │  ┌─────────────────────────────┐  │
         │  │  vLLM (lokalny LLM)         │  │
         │  │  :8000 (localhost)           │  │
         │  │  Qwen2.5-Coder-14B (AWQ)    │  │
         │  │  + Qwen2.5-7B (reasoning)   │  │
         │  │  GPU serwera Hetzner        │  │
         │  └─────────────────────────────┘  │
         │                                   │
         │  Alternatywnie: OpenAI API ───────┼──→ https://api.openai.com/v1
         │                                   │
         └───────────────┬───────────────────┘
                         │
                    Tailscale VPN
                    (100.122.147.29)
                         │
              ┌──────────┴──────────┐
              │  Komputer lokalny   │
              │  (SSH + zarządzanie)│
              │  100.90.234.17      │
              └─────────────────────┘
```

## Komponenty

### 1. DNS (home.pl)

- **Domena:** digitalunity.pl
- **Panel:** home.pl
- **Serwery DNS:** dns.home.pl, dns2.home.pl, dns3.home.pl
- **Rekord A:** `lem` → `144.76.2.68`
- **Wynikowy adres:** https://lem.digitalunity.pl

### 2. Serwer Hetzner

- **IP publiczne:** 144.76.2.68
- **IP Tailscale:** 100.122.147.29
- **IPv6:** 2a01:4f8:190:7248::2
- **System:** Ubuntu 22.04.5 LTS
- **Użytkownik:** kochnik
- **Dysk:** ~1.69 TB
- **Inne projekty na serwerze:** ai-lab, ms-harmonogramowanie-maili, orchestrator

### 3. Tailscale VPN

Dostęp SSH do serwera odbywa się przez sieć Tailscale:

```bash
ssh kochnik@100.122.147.29
```

- Serwer Hetzner jest podłączony do sieci Tailscale
- Komputer lokalny łączy się przez Tailscale (IP: 100.90.234.17)
- Umożliwia bezpieczne zarządzanie serwerem bez otwierania portu SSH na publiczny internet

### 4. Nginx (reverse proxy + SSL)

**Plik konfiguracji:** `/etc/nginx/sites-available/lem.digitalunity.pl`
**Symlink:** `/etc/nginx/sites-enabled/lem.digitalunity.pl`

Rola:
- Nasłuchuje na portach 80 i 443
- Port 80 → automatyczne przekierowanie na HTTPS
- Port 443 → terminacja SSL + proxy do Gunicorn na localhost:8010
- Przekazuje nagłówki: Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto
- Timeout: 120s

```bash
# Komendy zarządzania
sudo nginx -t                    # sprawdź konfigurację
sudo nginx -s reload             # przeładuj bez restartu
sudo systemctl restart nginx     # pełny restart
sudo systemctl status nginx      # status
```

### 5. Certyfikat SSL (Let's Encrypt)

- **Certyfikat:** `/etc/letsencrypt/live/lem.digitalunity.pl/fullchain.pem`
- **Klucz:** `/etc/letsencrypt/live/lem.digitalunity.pl/privkey.pem`
- **Wygasa:** 2026-05-24
- **Automatyczne odnawianie:** Tak (Certbot scheduled task)
- **Email:** katarzyna.ochnik@digitalunity.pl

```bash
sudo certbot renew               # ręczne odnowienie
sudo certbot certificates        # sprawdź status certyfikatów
```

### 6. Gunicorn + Uvicorn (serwer aplikacji)

**Ścieżka aplikacji:** `/home/kochnik/LEM/`
**Konfiguracja:** `/home/kochnik/LEM/gunicorn_config.py`
**Virtualenv:** `/home/kochnik/LEM/venv/`

Parametry:
- Bind: `0.0.0.0:8010`
- Workers: min(4, max(2, CPU count))
- Worker class: `uvicorn.workers.UvicornWorker`
- Timeout: 120s
- Logi błędów: `/home/kochnik/LEM/logs/error.log`
- Logi dostępu: `/home/kochnik/LEM/logs/access.log`

```bash
# Graceful restart (bez przerwy w działaniu)
kill -HUP $(pgrep -f 'gunicorn.*app.main' | head -1)

# Sprawdź czy działa
ps aux | grep gunicorn

# Zatrzymanie
kill $(pgrep -f 'gunicorn.*app.main' | head -1)

# Uruchomienie
cd ~/LEM && venv/bin/gunicorn app.main:app -c gunicorn_config.py --daemon
```

### 7. Lokalne modele LLM (vLLM)

Modele działają na GPU serwera Hetzner, serwowane przez vLLM na localhost.

| Model | Endpoint | Port | GPU util |
|-------|----------|------|----------|
| Qwen/Qwen2.5-Coder-14B-Instruct-AWQ | localhost:8000/v1 | 8000 | 0.8 |
| Qwen/Qwen2.5-7B-Instruct-AWQ (reasoning) | — | — | 0.35 |

Aplikacja może przełączać się między LLM lokalnym a OpenAI API (konfiguracja w `.env` i runtime).

### 8. OpenAI API (alternatywny provider)

- **Endpoint:** https://api.openai.com/v1
- **Domyślny model:** gpt-5-mini-2025-08-07
- **Dostępne modele:** gpt-4.1-2025-04-14, gpt-5.2-2025-12-11, gpt-5-mini-2025-08-07
- Przełączanie provider → przez UI aplikacji lub zmienną `LLM_PROVIDER` w `.env`

## Zmienne środowiskowe (.env)

Plik: `/home/kochnik/LEM/.env`

| Zmienna | Wartość | Opis |
|---------|---------|------|
| `LLM_PROVIDER` | `local` | Aktywny provider LLM (local / openai) |
| `LOCAL_LLM_BASE_URL` | `http://localhost:8000/v1` | Endpoint lokalnego vLLM |
| `LOCAL_LLM_MODEL` | `Qwen/Qwen2.5-Coder-14B-Instruct-AWQ` | Model lokalny |
| `LOCAL_MAX_LEN` | `4096` | Max długość kontekstu |
| `LOCAL_GPU_UTIL` | `0.8` | Wykorzystanie GPU (80%) |
| `SESSION_COOKIE_SECURE` | `true` | Cookie tylko przez HTTPS |
| `SESSION_COOKIE_SAMESITE` | `none` | Polityka SameSite |
| `CORS_ORIGINS` | `https://lem.digitalunity.pl` | Dozwolone originy CORS |

## Firewall (UFW)

```bash
sudo ufw status                  # sprawdź otwarte porty
```

Wymagane porty:
- **22** — SSH (dostęp przez Tailscale)
- **80** — HTTP (redirect do HTTPS)
- **443** — HTTPS
- **8010** — Gunicorn (tylko localhost, nie musi być otwarty na zewnątrz)

## Przepływ żądania

1. Użytkownik otwiera `https://lem.digitalunity.pl`
2. DNS (home.pl) rozwiązuje `lem.digitalunity.pl` → `144.76.2.68`
3. Nginx na porcie 443 odbiera żądanie, terminuje SSL
4. Nginx przekazuje (proxy_pass) do `http://127.0.0.1:8010`
5. Gunicorn/Uvicorn obsługuje FastAPI (`app.main:app`)
6. Jeśli ocena kompetencji → FastAPI wysyła prompt do vLLM na `localhost:8000` (lub OpenAI API)
7. Odpowiedź wraca tą samą drogą do użytkownika

## Rozwiązywanie problemów

### Strona nie odpowiada
```bash
sudo systemctl status nginx          # czy Nginx działa?
ps aux | grep gunicorn               # czy Gunicorn działa?
sudo tail -50 /var/log/nginx/error.log
tail -50 ~/LEM/logs/error.log
```

### Certyfikat wygasł
```bash
sudo certbot renew && sudo nginx -s reload
```

### LLM nie odpowiada
```bash
curl http://localhost:8000/v1/models  # czy vLLM działa?
```

### Po zmianach w kodzie
```bash
kill -HUP $(pgrep -f 'gunicorn.*app.main' | head -1)
```

### Po zmianach w .env
```bash
kill $(pgrep -f 'gunicorn.*app.main' | head -1)
cd ~/LEM && venv/bin/gunicorn app.main:app -c gunicorn_config.py --daemon
```

### Brak dostępu SSH
Sprawdź czy Tailscale działa na Twoim komputerze, potem:
```bash
ssh kochnik@100.122.147.29
```
