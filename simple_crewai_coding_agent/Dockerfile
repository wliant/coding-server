FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src/ ./src/
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["uv", "run", "simple-crewai-coding-agent"]
