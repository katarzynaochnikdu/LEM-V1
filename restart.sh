#!/bin/bash
pkill -f 'uvicorn app.main' 2>/dev/null
sleep 2
cd /home/kochnik/LEM
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 > logs/server.log 2>&1 &
sleep 3
curl -s http://localhost:8001/health
