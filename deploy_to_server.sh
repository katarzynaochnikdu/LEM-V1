#!/bin/bash
# Skrypt automatycznego wdrożenia systemu LEM na serwer
# Uruchom na serwerze: bash deploy_to_server.sh

set -e  # Zatrzymaj przy błędzie

echo "=================================="
echo "Wdrożenie systemu LEM na serwer"
echo "=================================="
echo ""

# Kolory dla outputu
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funkcja do wyświetlania komunikatów
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Sprawdź czy jesteśmy w katalogu LEM
if [ ! -f "requirements.txt" ]; then
    log_error "Nie znaleziono pliku requirements.txt. Upewnij się że jesteś w katalogu LEM."
    exit 1
fi

# 1. Aktualizacja systemu
log_info "Krok 1/8: Aktualizacja systemu..."
sudo apt update -qq

# 2. Instalacja wymaganych pakietów
log_info "Krok 2/9: Instalacja wymaganych pakietów..."
sudo apt install -y python3.11 python3.11-venv python3-pip nginx nodejs npm > /dev/null 2>&1 || {
    log_warn "Python 3.11 nie jest dostępny, próbuję python3..."
    sudo apt install -y python3 python3-venv python3-pip nginx nodejs npm
}

# 3. Utworzenie środowiska wirtualnego
log_info "Krok 3/9: Tworzenie środowiska wirtualnego..."
if [ -d "venv" ]; then
    log_warn "Środowisko wirtualne już istnieje, pomijam..."
else
    python3 -m venv venv
fi

# 4. Aktywacja i instalacja zależności
log_info "Krok 4/9: Instalacja zależności Python..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn -q

# 5. Konfiguracja .env
log_info "Krok 5/9: Konfiguracja zmiennych środowiskowych..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warn "Skopiowano .env.example do .env"
        log_warn "WAŻNE: Edytuj plik .env i dodaj OPENAI_API_KEY!"
        echo ""
        echo "Naciśnij Enter aby kontynuować po edycji .env..."
        read
    else
        log_error "Nie znaleziono .env.example"
        exit 1
    fi
else
    log_info ".env już istnieje"
fi

# Sprawdź czy OPENAI_API_KEY jest ustawiony
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    log_error "OPENAI_API_KEY nie jest ustawiony w .env!"
    log_error "Edytuj plik .env i dodaj: OPENAI_API_KEY=sk-twoj-klucz"
    exit 1
fi

# 6. Test aplikacji
log_info "Krok 6/9: Build frontendu React..."
FRONTEND_DIR="$(cd .. && pwd)/frontend"
if [ ! -d "$FRONTEND_DIR" ]; then
    log_error "Nie znaleziono katalogu frontend obok LEM V1: $FRONTEND_DIR"
    exit 1
fi

pushd "$FRONTEND_DIR" > /dev/null
if [ -f "package-lock.json" ]; then
    npm ci
else
    npm install
fi
npm run build
popd > /dev/null

if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
    log_error "Build frontendu nie utworzył pliku dist/index.html"
    exit 1
fi

log_info "Krok 7/9: Test aplikacji..."
python -c "from app.main import app; print('Import OK')" || {
    log_error "Nie udało się zaimportować aplikacji!"
    exit 1
}

# 8. Utworzenie katalogu na logi
log_info "Krok 8/9: Tworzenie katalogu na logi..."
mkdir -p logs

# 9. Konfiguracja Gunicorn
log_info "Krok 9/9: Konfiguracja Gunicorn..."
cat > gunicorn_config.py << 'EOF'
import multiprocessing
import os

# Ścieżka do katalogu projektu
base_dir = os.path.dirname(os.path.abspath(__file__))

bind = "0.0.0.0:8000"
workers = max(2, multiprocessing.cpu_count())
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
errorlog = os.path.join(base_dir, "logs", "error.log")
accesslog = os.path.join(base_dir, "logs", "access.log")
loglevel = "info"
EOF

log_info "Konfiguracja Gunicorn utworzona"

# 9. Konfiguracja systemd service
log_info "Tworzenie systemd service..."
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

sudo tee /etc/systemd/system/lem-api.service > /dev/null << EOF
[Unit]
Description=LEM Assessment API
After=network.target

[Service]
Type=notify
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
Environment="PYTHONPATH=$CURRENT_DIR"
ExecStart=$CURRENT_DIR/venv/bin/gunicorn app.main:app -c $CURRENT_DIR/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 10. Konfiguracja Nginx
log_info "Konfiguracja Nginx..."

# Pobierz IP Tailscale
TAILSCALE_IP=$(ip addr show tailscale0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "")

if [ -z "$TAILSCALE_IP" ]; then
    log_warn "Nie znaleziono IP Tailscale, używam localhost"
    SERVER_NAME="localhost"
else
    log_info "Znaleziono IP Tailscale: $TAILSCALE_IP"
    SERVER_NAME="$TAILSCALE_IP"
fi

sudo tee /etc/nginx/sites-available/lem-api > /dev/null << EOF
server {
    listen 80;
    server_name $SERVER_NAME _;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Aktywuj konfigurację Nginx
sudo ln -sf /etc/nginx/sites-available/lem-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test konfiguracji Nginx
sudo nginx -t || {
    log_error "Błąd w konfiguracji Nginx!"
    exit 1
}

# 11. Uruchomienie serwisów
log_info "Uruchamianie serwisów..."

# Przeładuj systemd
sudo systemctl daemon-reload

# Włącz autostart
sudo systemctl enable lem-api

# Uruchom service
sudo systemctl start lem-api

# Restart Nginx
sudo systemctl restart nginx

# Sprawdź status
sleep 2
if sudo systemctl is-active --quiet lem-api; then
    log_info "✓ Service lem-api działa!"
else
    log_error "✗ Service lem-api nie działa!"
    sudo systemctl status lem-api
    exit 1
fi

# 12. Test API
log_info "Test API..."
sleep 3

HEALTH_CHECK=$(curl -s http://localhost:8000/health || echo "FAILED")
if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    log_info "✓ API działa poprawnie!"
else
    log_error "✗ API nie odpowiada!"
    log_error "Sprawdź logi: sudo journalctl -u lem-api -n 50"
    exit 1
fi

# Podsumowanie
echo ""
echo "=================================="
echo -e "${GREEN}WDROŻENIE ZAKOŃCZONE SUKCESEM!${NC}"
echo "=================================="
echo ""
echo "API jest dostępne pod adresem:"
if [ -n "$TAILSCALE_IP" ]; then
    echo "  http://$TAILSCALE_IP/"
    echo "  http://$TAILSCALE_IP/docs (dokumentacja Swagger)"
else
    echo "  http://localhost/"
    echo "  http://localhost/docs (dokumentacja Swagger)"
fi
echo ""
echo "Przydatne komendy:"
echo "  sudo systemctl status lem-api    # Status serwisu"
echo "  sudo systemctl restart lem-api   # Restart serwisu"
echo "  sudo journalctl -u lem-api -f    # Logi na żywo"
echo "  tail -f logs/error.log           # Logi błędów"
echo "  tail -f logs/access.log          # Logi dostępu"
echo ""
echo "Test API:"
echo "  curl http://localhost/health"
echo ""
