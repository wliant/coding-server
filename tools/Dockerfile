FROM python:3.12-slim

WORKDIR /app

RUN adduser --system --uid 1001 appuser

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir ".[dev]"

USER appuser
EXPOSE 8002

CMD ["python", "-m", "tools.gateway"]
