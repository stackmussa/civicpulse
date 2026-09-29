# syntax=docker/dockerfile:1
# ── Stage 1: Builder stage ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_PREFERENCE=only-system \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv venv /opt/venv && uv sync --active --frozen --no-install-project

COPY . .
RUN uv sync --active --frozen

# ── Stage 2: Runtime stage (minimal production image) ───────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create non-root system user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Copy virtualenv and application from builder only
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --from=builder --chown=appuser:appuser /build/app /app/app
COPY --from=builder --chown=appuser:appuser /build/alembic /app/alembic
COPY --from=builder --chown=appuser:appuser /build/alembic.ini /app/alembic.ini
COPY --from=builder --chown=appuser:appuser /build/scripts /app/scripts

USER appuser

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

