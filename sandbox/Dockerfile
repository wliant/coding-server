FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl jq build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN adduser --system --uid 1001 appuser \
    && mkdir -p /home/appuser /workspace \
    && chown appuser /home/appuser /workspace

ENV HOME=/home/appuser

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir ".[dev]"

USER appuser
EXPOSE 8005

CMD ["uvicorn", "sandbox.app:app", "--host", "0.0.0.0", "--port", "8005"]
