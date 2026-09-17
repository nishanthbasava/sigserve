FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY sigserve ./sigserve
COPY alembic.ini ./
COPY migrations ./migrations

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "sigserve.main:app", "--host", "0.0.0.0", "--port", "8000"]
