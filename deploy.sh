#!/bin/bash
set -e

cd ~/lem_assessment

# Zatrzymaj serwer jeśli działa
pkill -f 'uvicorn.*main:app' || true
sleep 1

# Aktualizuj pliki
echo "Deploying updated files..."

# Uruchom serwer w tle
cd ~/lem_assessment
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 > logs/server.log 2>&1 &
sleep 2

# Sprawdź czy działa
if curl -s http://localhost:8001/health > /dev/null; then
    echo "Server started successfully!"
else
    echo "Server failed to start. Check logs/server.log"
    exit 1
fi
