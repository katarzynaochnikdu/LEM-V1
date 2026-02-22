# Wdrożenie LEM na serwer z Tailscale

## Szybkie wdrożenie (automatyczne)

Skoro jesteś już zalogowana na serwerze przez terminal, wykonaj:

### 1. Transfer plików na serwer

**Z lokalnej maszyny (Windows PowerShell):**

```powershell
# Znajdź IP Tailscale serwera (na serwerze uruchom: tailscale ip -4)
# Następnie skopiuj pliki:

scp -r c:\Users\kochn\.cursor\Daniel\LEM kochnik@100.x.x.x:/home/kochnik/
```

**Lub użyj WinSCP/FileZilla** z IP Tailscale.

### 2. Na serwerze uruchom skrypt automatycznego wdrożenia

```bash
cd /home/kochnik/LEM
chmod +x deploy_to_server.sh
./deploy_to_server.sh
```

Skrypt automatycznie:
- ✅ Zainstaluje wymagane pakiety
- ✅ Utworzy środowisko Python
- ✅ Zainstaluje zależności
- ✅ Skonfiguruje Gunicorn
- ✅ Utworzy systemd service
- ✅ Skonfiguruje Nginx
- ✅ Uruchomi API

### 3. Edycja .env (WAŻNE!)

Podczas instalacji skrypt poprosi Cię o edycję `.env`:

```bash
nano .env
```

Dodaj swój klucz OpenAI:
```
OPENAI_API_KEY=sk-twoj-klucz-tutaj
OPENAI_MODEL=gpt-4o
```

Zapisz (Ctrl+O, Enter) i wyjdź (Ctrl+X).

### 4. Gotowe!

API będzie dostępne pod:
- **Health check**: `http://TWOJ_TAILSCALE_IP/health`
- **Dokumentacja**: `http://TWOJ_TAILSCALE_IP/docs`
- **API**: `http://TWOJ_TAILSCALE_IP/assess`

---

## Sprawdzenie IP Tailscale

**Na serwerze:**
```bash
tailscale ip -4
# Wyświetli np: 100.64.1.5
```

**Na lokalnej maszynie (Windows):**
```powershell
tailscale ip -4
```

---

## Testowanie API

### Z lokalnej maszyny (przez Tailscale)

```powershell
# Health check
curl http://100.x.x.x/health

# Dokumentacja w przeglądarce
start http://100.x.x.x/docs

# Test oceny
curl -X POST "http://100.x.x.x/assess" `
  -H "Content-Type: application/json" `
  -d '{
    "participant_id": "TEST001",
    "response_text": "Przygotowując się do rozmowy delegującej analizuję priorytety kwartalne banku...",
    "case_id": "delegowanie_bnp_v1"
  }'
```

---

## Przydatne komendy (na serwerze)

### Status serwisu
```bash
sudo systemctl status lem-api
```

### Restart serwisu
```bash
sudo systemctl restart lem-api
```

### Logi na żywo
```bash
# Logi systemd
sudo journalctl -u lem-api -f

# Logi aplikacji
tail -f /home/kochnik/LEM/logs/error.log
tail -f /home/kochnik/LEM/logs/access.log
```

### Zatrzymanie serwisu
```bash
sudo systemctl stop lem-api
```

### Sprawdzenie czy port 8000 jest zajęty
```bash
sudo netstat -tulpn | grep 8000
```

---

## Aktualizacja aplikacji

```bash
cd /home/kochnik/LEM

# Jeśli używasz Git:
git pull

# Restart serwisu
sudo systemctl restart lem-api
```

---

## Troubleshooting

### Problem: Skrypt nie działa

```bash
# Sprawdź uprawnienia
chmod +x deploy_to_server.sh

# Uruchom ponownie
./deploy_to_server.sh
```

### Problem: Service nie startuje

```bash
# Sprawdź logi
sudo journalctl -u lem-api -n 100

# Sprawdź czy .env ma klucz API
cat .env | grep OPENAI_API_KEY

# Sprawdź czy środowisko Python działa
cd /home/kochnik/LEM
source venv/bin/activate
python -c "from app.main import app; print('OK')"
```

### Problem: Nginx 502 Bad Gateway

```bash
# Sprawdź czy Gunicorn działa
sudo systemctl status lem-api

# Sprawdź logi Nginx
sudo tail -f /var/log/nginx/error.log

# Restart obu serwisów
sudo systemctl restart lem-api
sudo systemctl restart nginx
```

### Problem: Nie mogę połączyć się z API

```bash
# Sprawdź firewall
sudo ufw status

# Jeśli firewall jest włączony, zezwól na port 80:
sudo ufw allow 80/tcp

# Sprawdź czy Nginx nasłuchuje
sudo netstat -tulpn | grep :80
```

---

## Bezpieczeństwo przez Tailscale

Ponieważ używasz Tailscale:
- ✅ Połączenie jest szyfrowane end-to-end
- ✅ Nie musisz otwierać portów na firewall publiczny
- ✅ Dostęp tylko dla urządzeń w Twojej sieci Tailscale
- ✅ Nie potrzebujesz domeny ani certyfikatu SSL

**Zalecenie**: Zostaw firewall tak jak jest - Tailscale zapewnia bezpieczeństwo.

---

## Koszty

- **Serwer VPS**: $5-10/miesiąc (2GB RAM, 2 CPU)
- **Tailscale**: Darmowy (do 100 urządzeń)
- **OpenAI API**: ~$0.10-0.15 na ocenę
- **Nginx**: Darmowy

**Szacunek**: ~$5-10/miesiąc + koszty API OpenAI

---

## Następne kroki

Po wdrożeniu:

1. ✅ Przetestuj API z przykładową odpowiedzią
2. ✅ Sprawdź dokumentację Swagger: `http://TWOJ_IP/docs`
3. ✅ Uruchom testy: `python tests/run_manual_test.py`
4. ✅ Rozpocznij kalibrację (patrz `CALIBRATION_GUIDE.md`)

---

## Kontakt

W razie problemów:
1. Sprawdź logi: `sudo journalctl -u lem-api -n 100`
2. Sprawdź dokumentację: `README.md`, `INSTALLATION.md`
3. Sprawdź status: `sudo systemctl status lem-api`
