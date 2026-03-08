FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

RUN adduser --system --uid 1001 appuser && mkdir -p /home/appuser && chown appuser /home/appuser

ENV HOME=/home/appuser

# Copy agent source so the path dependency resolves: worker/pyproject.toml -> ../agents/...
COPY agents/simple_crewai_pair_agent/ ./agents/simple_crewai_pair_agent/

# Install worker package from its own directory so ../agents/... resolves correctly
COPY worker/pyproject.toml ./worker/
COPY worker/src/ ./worker/src/
COPY worker/alembic/ ./worker/alembic/
WORKDIR /app/worker
RUN pip install --no-cache-dir ".[dev]"
WORKDIR /app

USER appuser
EXPOSE 8001

CMD ["uvicorn", "worker.app:app", "--host", "0.0.0.0", "--port", "8001"]
