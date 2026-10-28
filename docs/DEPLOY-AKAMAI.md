# Deploying WarRoom on Akamai Cloud (Linode)

A single-instance deployment: one Linode runs Postgres, the FastAPI backend, the
nginx-served frontend and Caddy (automatic HTTPS), all via Docker Compose.
This fits WarRoom's load (one writer process, a few hundred MB of data) and
keeps cost and moving parts low. A scale-out option is at the end.

```
            Internet
               │ 443/80
        ┌──────▼──────┐   Akamai Cloud Firewall: 80, 443 open; 22 from admin IPs only
        │    Caddy    │   TLS (Let's Encrypt), HSTS, gzip/zstd
        └──┬───────┬──┘
   /api/*  │       │  /*
   ┌───────▼──┐ ┌──▼────────┐
   │ backend  │ │ frontend  │  FastAPI + APScheduler   |  nginx static build
   └───────┬──┘ └───────────┘
           │ private docker network
     ┌─────▼─────┐
     │ Postgres  │  volume: pgdata  → nightly pg_dump → Object Storage
     └───────────┘
```

---

## 0. Pre-flight: can Akamai reach our data sources?

WarRoom is only useful if its ~130 upstream sources answer from the server's
IP. Datacenter IP ranges (Akamai's ASN 63949 included) are treated more
harshly than home connections by Cloudflare-fronted sites, Reddit, Yahoo
Finance and Google News. **Test from a throwaway instance in the region you
plan to use before committing.**

```bash
# On a fresh Nanode (Ubuntu 24.04) in the target region
apt-get update && apt-get install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | sh && . ~/.local/bin/env
git clone https://github.com/arnarun/WarRoom.git && cd WarRoom/backend
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/probe_sources.py --json probe-akamai.json
```

The probe uses the same clients, headers and URL lists as the real fetchers and
prints one line per source (`✓ OK`, `∅ EMPTY`, `⛔ BLOCKED`, `✗ ERROR`) plus the
egress IP/rDNS. Delete the Nanode afterwards (billing is hourly).

### Results: home vs. Akamai Toronto (2026-10-27)

| | Home (residential) | Akamai Toronto |
|---|---|---|
| Checks passing (before fixes) | 118 / 133 | 115 / 133 |
| Yahoo Finance, Google News | OK | OK |

Only three sources failed from Akamai but not from home. All three are fixed
by changes in the app:

| Source | Akamai result | Fix |
|---|---|---|
| Indian Express | Blocked | Now read through a Google News `site:indianexpress.com` feed |
| VentureBeat | 429 Too Many Requests | The app hit the site 3× per sweep; now 2 Google News feeds, duplicate removed from `breach.py` |
| NVD | Timeout | Timeout raised to 90 s with one retry; optional `NVD_API_KEY`; CISA KEV added as a fast, key-free source |

The failures seen from both networks are fixed too:

| Source | Was | Now |
|---|---|---|
| AP News | 403 Cloudflare | Google News `site:apnews.com` |
| Hindustan Times | HTML instead of RSS | `feeds/rss/india-news/rssfeed.xml` |
| Hacker News Best | 404 | `hnrss.org/best` |
| ENISA | 404 | Google News `site:enisa.europa.eu` |
| BSI | 404 | CERT-Bund WID advisory feed |
| SOCRadar | 403 | Replaced by The Record (therecord.media) |
| StockTwits | 403 Cloudflare | Fetched with `curl_cffi` Chrome impersonation |
| GDELT | 429 | 6 s spacing; stops the cycle on a rate-limit reply instead of extending the penalty |
| abuse.ch URLhaus / MalwareBazaar | 401 | Need `ABUSECH_AUTH_KEY` (free, auth.abuse.ch); skipped without it. Feodo Tracker added (no key) |
| AlienVault OTX | RSS discontinued | OTX API with `OTX_API_KEY` (free); skipped without it |
| Reddit | 403 | Needs `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` (free Reddit app). No key-free option |

After the fixes, from home: all 106 RSS feeds, 16 OSINT checks and every
social source except Reddit pass. Sources waiting on a key show as
`– SKIPPED` in the probe. **Re-run the probe on the Akamai instance to confirm.**

**Go / no-go:** go, once the probe re-run on Akamai matches the home results.
If a source later starts failing only from the server, a Google News
`site:` feed is the usual fallback.

---

## 1. Provision

**Instance:** Shared CPU, 4 GB RAM / 2 vCPU, Ubuntu 24.04 LTS (2 GB works but
the image builds and pandas/yfinance are memory-hungry). Pick the region
closest to your users that passed the probe. Enable **Backups** (Linode
Backup service) for whole-disk snapshots.

**Cloud Firewall** (attach to the Linode):

| Direction | Port | Source | Purpose |
|---|---|---|---|
| Inbound | 22/tcp | your admin IP(s) only | SSH |
| Inbound | 80/tcp, 443/tcp, 443/udp | 0.0.0.0/0, ::/0 | HTTP → HTTPS redirect, HTTPS, HTTP/3 |
| Inbound | everything else | — | Drop |
| Outbound | all | — | Fetchers need broad egress |

**DNS:** create an `A` (and `AAAA`) record for e.g. `warroom.example.com`
pointing at the Linode's IPs. Caddy needs this resolving before it can issue
a certificate.

## 2. Harden the host

```bash
# as root, once
adduser deploy && usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
apt-get update && apt-get -y upgrade && apt-get install -y unattended-upgrades fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades
timedatectl set-timezone UTC
```

Install Docker Engine + Compose plugin from Docker's official apt repository
(docs.docker.com/engine/install/ubuntu), then `usermod -aG docker deploy`.

## 3. Deploy

```bash
sudo mkdir -p /opt/warroom && sudo chown deploy: /opt/warroom
git clone https://github.com/arnarun/WarRoom.git /opt/warroom
cd /opt/warroom
cp .env.example .env && chmod 600 .env
```

Edit `.env` — the production values that matter:

```ini
DOMAIN=warroom.example.com
ACME_EMAIL=ops@example.com
POSTGRES_PASSWORD=<openssl rand -base64 32>
DATABASE_SSL=false              # db is on the private docker network
RETENTION_DAYS_ARTICLES=30
RETENTION_DAYS_OSINT=30
RETENTION_DAYS_SOCIAL=14
# free keys (recommended)
NVD_API_KEY=
ABUSECH_AUTH_KEY=
OTX_API_KEY=
# optional sources
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
GUARDIAN_API_KEY=
NEWSDATA_API_KEY=
```

`DATABASE_URL`, `CORS_ORIGINS` and `VITE_API_URL` are set by
`deploy/akamai/docker-compose.prod.yml` (same-origin setup — no CORS needed).

```bash
docker compose -f deploy/akamai/docker-compose.prod.yml --env-file .env up -d --build
docker compose -f deploy/akamai/docker-compose.prod.yml logs -f backend   # watch first sweep
```

## 4. Verify

```bash
curl -s https://warroom.example.com/api/health      # {"status":"ok","db":"up","version":"1.1.0"}
curl -s https://warroom.example.com/api/status | jq '.rss | {ok, empty, fail, failing}'
curl -sI https://warroom.example.com | grep -i -E 'strict-transport|content-security'
```

Then open the site → **Status** tab: every job should show `ok` within ~30 min,
and the RSS failing list should match what the pre-flight probe predicted.

## 5. Operations

**Backups** — whole-disk via Linode Backups, plus logical dumps:

```bash
sudo tee /etc/cron.d/warroom-backup <<<'15 3 * * * root /opt/warroom/deploy/akamai/backup.sh'
```

Ship `/var/backups/warroom` to Akamai Object Storage (rclone/s3cmd) for
off-box copies. Restore: `pg_restore -U warroom -d warroom --clean < file.dump`
inside the `db` container.

**Monitoring** — point an external uptime check (e.g. Linode/Akamai alerts,
UptimeRobot) at `/api/health` (returns 503 when the DB is down). Check
`/api/status` weekly for feeds that have started failing.

**Updates**

```bash
cd /opt/warroom && git pull
docker compose -f deploy/akamai/docker-compose.prod.yml --env-file .env up -d --build
docker image prune -f
```

Migrations run automatically on backend start. Roll back with
`git checkout <previous-sha>` and the same `up -d --build`.

**Logs** — `docker compose ... logs --since 1h backend`. Docker's default
json-file driver grows unbounded; add to `/etc/docker/daemon.json`:
`{"log-driver":"json-file","log-opts":{"max-size":"20m","max-file":"5"}}`.

## 6. Cut-over from Railway

1. Run the pre-flight probe; fix blockers.
2. Deploy on Akamai under a temporary hostname; let it run 24 h.
3. Optionally carry data over: `pg_dump` from Railway → `pg_restore` into the
   new `db` container (retention will prune anything > 30 days anyway).
4. Point the production DNS name at the Linode; keep Railway up until DNS TTL
   has expired, then shut it down.

## 7. Scaling later (not needed now)

- **Akamai Managed Database for PostgreSQL** instead of the `db` container —
  set `DATABASE_URL` to the managed host and `DATABASE_SSL=true`; restrict its
  allow-list to the Linode's IP.
- **LKE (Kubernetes)** only if you need multiple backend replicas. Note the
  scheduler must then run in exactly one pod (split fetchers into a separate
  worker deployment with `replicas: 1`), or jobs will run N times.
- **Akamai CDN** in front of Caddy for the static frontend if traffic grows.

## Checklist

- [ ] Pre-flight probe from target region compared against baseline
- [ ] Free keys obtained: NVD, abuse.ch Auth-Key, OTX; Reddit app credentials (optional)
- [ ] Linode 4 GB + Backups, Cloud Firewall attached, DNS records created
- [ ] Host hardened (non-root user, key-only SSH, unattended upgrades)
- [ ] `.env` filled, `chmod 600`, strong `POSTGRES_PASSWORD`
- [ ] Stack up; `/api/health` OK; HTTPS + HSTS + CSP headers present
- [ ] Backup cron installed and one restore tested
- [ ] Uptime check on `/api/health`
- [ ] Docker log rotation configured
