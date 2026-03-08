FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]" && playwright install --with-deps chromium
COPY . .
CMD ["pytest", "tests/", "-v", "--tb=short"]
