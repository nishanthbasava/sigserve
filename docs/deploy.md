# Deploying SigServe on AWS EC2

One VM running the production compose stack behind Caddy: the web UI and
API share one origin (Caddy routes `/api/*` and the bare API paths to the
api container, everything else to the web container). Sampler jobs are
CPU-bound MCMC, so favor compute over memory.

## 1. Provision

- **Instance**: t3.medium or better (2 vCPU / 4 GB; the worker image alone is
  ~1.8 GB and a sampler run keeps one core busy). Ubuntu 24.04 LTS.
- **Storage**: 20 GB gp3 minimum.
- **Security group**: inbound 22 (your IP only), 80, 443. Nothing else —
  Postgres and Redis are not published.
- **DNS**: point an A record (e.g. `sigserve.example.com`) at the instance's
  public IP. Caddy needs this to issue Let's Encrypt certificates.

## 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # log out and back in
```

## 3. Configure and start

```bash
git clone https://github.com/nishanthbasava/sigserve.git && cd sigserve
cp .env.example .env
# Edit .env:
#  - set a strong POSTGRES_PASSWORD and mirror it in DATABASE_URL
#  - set SIGSERVE_DOMAIN to your A record (Caddy reads it for TLS)
docker compose -f docker-compose.prod.yml up -d --build
```

The first build compiles the R worker image and takes several minutes. The
API container applies database migrations on startup.

## 4. Smoke test

Open `https://<your-domain>/` — the web UI mints its own key; click
"Try the sample dataset" and run it. Or over curl:

```bash
curl https://<your-domain>/health
KEY=$(curl -s -X POST https://<your-domain>/keys \
    -H "Content-Type: application/json" -d '{"name":"smoke"}' | jq -r .key)
curl https://<your-domain>/jobs -X POST \
    -H "Content-Type: application/json" -H "X-API-Key: $KEY" \
    -d '{"matrix": [[4,2],[1,3]], "params": {"rank": 2, "max_iters": 500}}'
```

(`python -m sigserve.cli create-key --name <who>` still works for
operator-issued keys.)

## Public-instance guards

Self-serve key minting and job submission are rate-limited per rolling
hour (`KEY_MINT_PER_HOUR`, default 10 per IP; `JOBS_PER_KEY_PER_HOUR`,
default 50). `JOB_TIMEOUT_SECONDS` (default 3600) caps a single fit, and
the maintenance service prunes terminal jobs after `JOB_RETENTION_DAYS`
(default 30) — the UI states this. Result pages are readable without a
key by anyone holding the job's URL (the random UUID is the capability);
listings and submission always require a key.

## 5. Operate

- **Update**: `git pull && docker compose -f docker-compose.prod.yml up -d --build`
- **Logs**: `docker compose -f docker-compose.prod.yml logs -f api worker`
- **Backup**: `docker compose -f docker-compose.prod.yml exec postgres pg_dump -U sigserve sigserve > backup.sql`
- **Scale workers**: `docker compose -f docker-compose.prod.yml up -d --scale worker=2`
  (one concurrent sampler job per worker; scale with vCPUs)
