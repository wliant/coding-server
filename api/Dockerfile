FROM python:3.12-slim

WORKDIR /app

RUN adduser --system --uid 1001 appuser

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/
COPY alembic.ini* ./
COPY alembic/ ./alembic/ 2>/dev/null || true
COPY scripts/ ./scripts/

USER appuser
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
