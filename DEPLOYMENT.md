# Instrukcja Wdrożenia na Serwer - System LEM

## Przygotowanie do wdrożenia

### Wymagania serwera

- **System**: Linux (Ubuntu 20.04+ zalecane) lub Windows Server
- **Python**: 3.11 lub nowszy
- **RAM**: minimum 2GB (zalecane 4GB)
- **Dysk**: ~2GB wolnego miejsca
- **Porty**: 80 (HTTP) i/lub 443 (HTTPS)
- **Dostęp**: SSH lub RDP

---

## Scenariusz A: Wdrożenie na Linux (Ubuntu/Debian)

### 1. Przygotowanie serwera

```bash
# Zaloguj się jako root lub użytkownik z sudo
ssh kochnik@twoj-serwer

# Aktualizacja systemu
sudo apt update && sudo apt upgrade -y

# Instalacja wymaganych pakietów
sudo apt install -y python3.11 python3.11-venv python3-pip nginx git

# Instalacja certbot (opcjonalnie, dla HTTPS)
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Transfer projektu na serwer

**Opcja A: Przez SCP (z Windows)**

```powershell
# Z lokalnej maszyny Windows (PowerShell):
scp -r c:\Users\kochn\.cursor\Daniel\LEM kochnik@twoj-serwer:/home/kochnik/
```

**Opcja B: Przez Git (jeśli projekt jest w repo)**

```bash
# Na serwerze:
cd /home/kochnik
git clone <repository-url> LEM
cd LEM
```

**Opcja C: Przez WinSCP** (GUI dla Windows)
- Pobierz WinSCP: https://winscp.net/
- Połącz się z serwerem
- Przeciągnij folder `LEM` na serwer

### 3. Konfiguracja środowiska Python

```bash
# Na serwerze:
cd /home/kochnik/LEM

# Utwórz środowisko wirtualne
python3.11 -m venv venv

# Aktywuj środowisko
source venv/bin/activate

# Zainstaluj zależności
pip install --upgrade pip
pip install -r requirements.txt

# Zainstaluj dodatkowe pakiety produkcyjne
pip install gunicorn
```

### 4. Konfiguracja zmiennych środowiskowych

```bash
# Skopiuj przykładowy plik .env
cp .env.example .env

# Edytuj plik .env
nano .env
```

**Zawartość `.env`**:
```
OPENAI_API_KEY=sk-twoj-klucz-tutaj
OPENAI_MODEL=gpt-4o
```

Zapisz (Ctrl+O, Enter) i wyjdź (Ctrl+X).

### 5. Test lokalny

```bash
# Test czy aplikacja działa
python -m pytest tests/ -v

# Uruchom serwer testowo
uvicorn app.main:app --host 0.0.0.0 --port 8000

# W innym terminalu/oknie:
curl http://localhost:8000/health
# Powinno zwrócić: {"status":"healthy","version":"1.0.0"}
```

Zatrzymaj serwer (Ctrl+C).

### 6. Konfiguracja Gunicorn (produkcja)

Utwórz plik konfiguracyjny Gunicorn:

```bash
nano gunicorn_config.py
```

**Zawartość**:
```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
errorlog = "/home/kochnik/LEM/logs/error.log"
accesslog = "/home/kochnik/LEM/logs/access.log"
loglevel = "info"
```

Utwórz katalog na logi:
```bash
mkdir -p /home/kochnik/LEM/logs
```

### 7. Konfiguracja Systemd (autostart)

Utwórz plik service:

```bash
sudo nano /etc/systemd/system/lem-api.service
```

**Zawartość**:
```ini
[Unit]
Description=LEM Assessment API
After=network.target

[Service]
Type=notify
User=kochnik
Group=kochnik
WorkingDirectory=/home/kochnik/LEM
Environment="PATH=/home/kochnik/LEM/venv/bin"
Environment="PYTHONPATH=/home/kochnik/LEM"
ExecStart=/home/kochnik/LEM/venv/bin/gunicorn app.main:app -c /home/kochnik/LEM/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Zapisz i aktywuj service:

```bash
# Przeładuj systemd
sudo systemctl daemon-reload

# Włącz autostart
sudo systemctl enable lem-api

# Uruchom service
sudo systemctl start lem-api

# Sprawdź status
sudo systemctl status lem-api

# Sprawdź logi
sudo journalctl -u lem-api -f
```

### 8. Konfiguracja Nginx (reverse proxy)

Utwórz konfigurację Nginx:

```bash
sudo nano /etc/nginx/sites-available/lem-api
```

**Zawartość (HTTP)**:
```nginx
server {
    listen 80;
    server_name twoja-domena.com;  # Lub IP serwera

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

Aktywuj konfigurację:

```bash
# Utwórz symlink
sudo ln -s /etc/nginx/sites-available/lem-api /etc/nginx/sites-enabled/

# Usuń domyślną konfigurację (opcjonalnie)
sudo rm /etc/nginx/sites-enabled/default

# Test konfiguracji
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 9. Konfiguracja HTTPS (opcjonalnie, zalecane)

```bash
# Uzyskaj certyfikat SSL (Let's Encrypt)
sudo certbot --nginx -d twoja-domena.com

# Certbot automatycznie zaktualizuje konfigurację Nginx
# i ustawi przekierowanie HTTP → HTTPS
```

### 10. Weryfikacja wdrożenia

```bash
# Test health check
curl http://twoja-domena.com/health

# Test API docs
curl http://twoja-domena.com/docs
# Lub otwórz w przeglądarce: http://twoja-domena.com/docs

# Test oceny (przykład)
curl -X POST "http://twoja-domena.com/assess" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "TEST001",
    "response_text": "Przygotowując się do rozmowy...",
    "case_id": "delegowanie_bnp_v1"
  }'
```

---

## Scenariusz B: Wdrożenie na Windows Server

### 1. Przygotowanie serwera

```powershell
# Zainstaluj Python 3.11+ z python.org
# Dodaj Python do PATH podczas instalacji

# Sprawdź instalację
python --version
```

### 2. Transfer projektu

Skopiuj folder `LEM` na serwer (np. do `C:\inetpub\LEM`).

### 3. Konfiguracja środowiska

```powershell
cd C:\inetpub\LEM

# Utwórz środowisko wirtualne
python -m venv venv

# Aktywuj
.\venv\Scripts\Activate.ps1

# Zainstaluj zależności
pip install -r requirements.txt
pip install waitress
```

### 4. Konfiguracja .env

Skopiuj `.env.example` do `.env` i edytuj:
```
OPENAI_API_KEY=sk-twoj-klucz-tutaj
OPENAI_MODEL=gpt-4o
```

### 5. Uruchomienie jako Windows Service

Utwórz plik `run_server.py`:

```python
from waitress import serve
from app.main import app

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8000, threads=4)
```

Użyj NSSM (Non-Sucking Service Manager) do utworzenia service:

```powershell
# Pobierz NSSM: https://nssm.cc/download
# Zainstaluj jako service
nssm install LEM-API "C:\inetpub\LEM\venv\Scripts\python.exe" "C:\inetpub\LEM\run_server.py"
nssm set LEM-API AppDirectory "C:\inetpub\LEM"
nssm start LEM-API
```

### 6. Konfiguracja IIS (reverse proxy)

- Zainstaluj IIS
- Zainstaluj URL Rewrite module
- Utwórz nową witrynę wskazującą na aplikację na porcie 8000

---

## Monitoring i utrzymanie

### Sprawdzanie logów

**Linux**:
```bash
# Logi systemd
sudo journalctl -u lem-api -f

# Logi Gunicorn
tail -f /home/kochnik/LEM/logs/error.log
tail -f /home/kochnik/LEM/logs/access.log

# Logi Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

**Windows**:
```powershell
# Event Viewer → Windows Logs → Application
```

### Restart serwisu

**Linux**:
```bash
sudo systemctl restart lem-api
sudo systemctl restart nginx
```

**Windows**:
```powershell
Restart-Service LEM-API
```

### Aktualizacja aplikacji

```bash
# Na serwerze
cd /home/kochnik/LEM
git pull  # Jeśli używasz Git
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart lem-api
```

---

## Bezpieczeństwo

### Firewall (Linux)

```bash
# Zezwól na HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

### Zmienne środowiskowe

**NIGDY** nie commituj pliku `.env` do repozytorium!

### Rate limiting (opcjonalnie)

Dodaj do Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /assess {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
```

---

## Troubleshooting

### Problem: Service nie startuje

```bash
# Sprawdź logi
sudo journalctl -u lem-api -n 50

# Sprawdź czy port jest zajęty
sudo netstat -tulpn | grep 8000

# Sprawdź uprawnienia
ls -la /home/kochnik/LEM
```

### Problem: Nginx 502 Bad Gateway

```bash
# Sprawdź czy Gunicorn działa
sudo systemctl status lem-api

# Sprawdź logi Nginx
sudo tail -f /var/log/nginx/error.log
```

### Problem: OpenAI API timeout

Zwiększ timeout w `gunicorn_config.py`:
```python
timeout = 300  # 5 minut
```

---

## Koszty i wydajność

### Szacunkowe koszty serwera

- **VPS (2GB RAM, 2 CPU)**: $5-10/miesiąc (DigitalOcean, Linode, Hetzner)
- **OpenAI API**: ~$0.10-0.15 na ocenę
- **SSL certyfikat**: Darmowy (Let's Encrypt)

### Wydajność

- **1 ocena**: ~20-30 sekund
- **Równoległe oceny**: ~4-8 jednocześnie (zależnie od CPU)
- **100 ocen**: ~30-40 minut

---

## Kontakt i wsparcie

W razie problemów sprawdź:
1. Logi systemd/Gunicorn
2. Logi Nginx
3. Dokumentację projektu: `README.md`, `INSTALLATION.md`

**Status serwisu**: `http://twoja-domena.com/health`
