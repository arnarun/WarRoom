#!/bin/sh
set -e
# Substitute only ${PORT} and ${BACKEND_URL} — leave nginx vars like $host, $remote_addr intact
envsubst '$PORT $BACKEND_URL' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
