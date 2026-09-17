# Deploying SigServe on AWS EC2

One VM running the production compose stack behind Caddy. Sampler jobs are
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
# Edit .env: set a strong POSTGRES_PASSWORD and mirror it in DATABASE_URL.
export SIGSERVE_DOMAIN=sigserve.example.com
docker compose -f docker-compose.prod.yml up -d --build
```

The first build compiles the R worker image and takes several minutes. The
API container applies database migrations on startup.

## 4. Mint a key and smoke test

```bash
docker compose -f docker-compose.prod.yml exec api \
    python -m sigserve.cli create-key --name first-user

curl https://$SIGSERVE_DOMAIN/health
curl https://$SIGSERVE_DOMAIN/jobs -X POST \
    -H "Content-Type: application/json" -H "X-API-Key: <key>" \
    -d '{"matrix": [[4,2],[1,3]], "params": {"rank": 2, "max_iters": 500}}'
```

## 5. Operate

- **Update**: `git pull && docker compose -f docker-compose.prod.yml up -d --build`
- **Logs**: `docker compose -f docker-compose.prod.yml logs -f api worker`
- **Backup**: `docker compose -f docker-compose.prod.yml exec postgres pg_dump -U sigserve sigserve > backup.sql`
- **Scale workers**: `docker compose -f docker-compose.prod.yml up -d --scale worker=2`
  (one concurrent sampler job per worker; scale with vCPUs)
