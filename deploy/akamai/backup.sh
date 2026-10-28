#!/bin/sh
# Nightly Postgres dump, kept 14 days. Install with:
#   echo '15 3 * * * root /opt/warroom/deploy/akamai/backup.sh' > /etc/cron.d/warroom-backup
# Copy /var/backups/warroom off-box (Akamai Object Storage via s3cmd/rclone) for real DR.
set -eu
DIR=/var/backups/warroom
mkdir -p "$DIR"
cd /opt/warroom
docker compose -f deploy/akamai/docker-compose.prod.yml --env-file .env exec -T db \
  pg_dump -U warroom -d warroom --format=custom > "$DIR/warroom-$(date +%F).dump"
find "$DIR" -name 'warroom-*.dump' -mtime +14 -delete
