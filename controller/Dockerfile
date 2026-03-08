FROM python:3.12-slim

WORKDIR /app

RUN adduser --system --uid 1001 appuser && mkdir -p /home/appuser && chown appuser /home/appuser

ENV HOME=/home/appuser

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir ".[dev]"

USER appuser
EXPOSE 8003

CMD ["uvicorn", "controller.app:app", "--host", "0.0.0.0", "--port", "8003"]
