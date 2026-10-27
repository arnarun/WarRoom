#!/bin/sh
set -e

echo "=== WarRoom Backend Starting ==="
echo "PORT: ${PORT:-8000}"

# Schema creation + migrations run in the app's lifespan (maintenance.migrate)
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
