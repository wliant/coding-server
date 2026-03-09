FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

RUN adduser --system --uid 1001 appuser && mkdir -p /home/appuser && chown appuser /home/appuser

ENV HOME=/home/appuser

COPY pyproject.toml ./
COPY src/ ./src/
COPY alembic/ ./alembic/
RUN pip install --no-cache-dir ".[dev]"

USER appuser
EXPOSE 8004

CMD ["uvicorn", "worker.app:app", "--host", "0.0.0.0", "--port", "8004"]
