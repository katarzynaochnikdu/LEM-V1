#!/bin/bash
curl -s -c /tmp/lem_cookies3.txt -X POST http://localhost:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}'
echo ""
curl -s -b /tmp/lem_cookies3.txt http://localhost:8001/api/prompts
