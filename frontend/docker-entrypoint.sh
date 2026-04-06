#!/bin/sh
set -e

# Apply defaults so nginx never gets an empty proxy_pass URL
export PORT="${PORT:-80}"
export BACKEND_URL="${BACKEND_URL:-http://backend.railway.internal:8000}"

echo "=== WarRoom Frontend ==="
echo "PORT: $PORT"
echo "BACKEND_URL: $BACKEND_URL"

# Substitute only ${PORT} and ${BACKEND_URL} — leave nginx vars ($host, $remote_addr) intact
envsubst '$PORT $BACKEND_URL' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf

echo "Generated nginx config:"
cat /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
