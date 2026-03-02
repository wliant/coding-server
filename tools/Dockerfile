FROM python:3.12-slim

WORKDIR /app

RUN adduser --system --uid 1001 appuser

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/

USER appuser
EXPOSE 8002

CMD ["python", "-m", "tools.gateway"]
