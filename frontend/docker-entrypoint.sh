#!/bin/sh
set -e
export PORT="${PORT:-80}"
echo "=== WarRoom Frontend — port $PORT ==="
envsubst '$PORT' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
