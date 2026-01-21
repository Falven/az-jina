# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.13.1-slim-bookworm
ARG UV_VERSION=0.5.30

FROM python:${PYTHON_VERSION} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --version ${UV_VERSION}

ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project

COPY auth_service ./auth_service
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    HOME=/app

RUN groupadd -r appuser --gid 10001 \
    && useradd -r -g appuser --uid 10001 -d /app appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/auth_service /app/auth_service
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

USER appuser

EXPOSE 8080
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=1s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen(http://127.0.0.1:8080/healthz, timeout=0.5)"

CMD ["python", "-m", "auth_service"]
