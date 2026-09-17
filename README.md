# SigServe

A REST API and job queue around [bayesNMF](https://github.com/jennalandy/bayesNMF) —
submit mutation-count matrices over HTTP and poll for Bayesian NMF mutational
signature results, no R required on the client.

## Architecture

- **FastAPI** — job submission and polling endpoints, API-key auth
- **Redis + RQ** — job queue; workers run the bayesNMF Gibbs sampler via rpy2
- **PostgreSQL** — job store (status, parameters, results)
- **Docker Compose** — local development stack

## Development

Requires Python 3.11+.

```bash
uv venv --python 3.13
uv pip install -e ".[dev]"
.venv/bin/pytest
```

Integration tests run against the full docker-compose stack:

```bash
cp .env.example .env
docker compose up -d --build
.venv/bin/pytest -m integration
```

## Status

Early development.
