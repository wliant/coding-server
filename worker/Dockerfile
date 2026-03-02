FROM python:3.12-slim

WORKDIR /app

RUN adduser --system --uid 1001 appuser

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/

USER appuser
EXPOSE 8001

CMD ["uvicorn", "worker.worker:app", "--host", "0.0.0.0", "--port", "8001"]
