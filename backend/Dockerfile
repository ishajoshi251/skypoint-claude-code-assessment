# =============================================================================
# TalentBridge — Backend Dockerfile (multi-stage)
# Builder: installs all deps into system Python (no venv needed inside Docker)
# Runtime: slim image, non-root user, copies site-packages from builder
# =============================================================================

ARG PYTHON_VERSION=3.11-slim

# ---------------------------------------------------------------------------
# Stage 1: builder — compile native extensions + install deps
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS builder

WORKDIR /build

# System deps needed to compile native extensions (asyncpg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip uv

COPY pyproject.toml ./

# Install torch CPU-only FIRST to lock the version before sentence-transformers
# pulls in torch 2.11+ which made cuda-toolkit a hard dependency (multi-GB download)
RUN uv pip install --system --no-cache \
    "torch==2.2.2" \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Install all remaining production deps into system Python
RUN uv pip install --system --no-cache .

# Verify key binaries exist (fail fast if something went wrong)
RUN alembic --version && uvicorn --version && python -c "import fastapi"

# ---------------------------------------------------------------------------
# Stage 2: runtime — slim, non-root
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS runtime

# Runtime system deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy CLI entry-point scripts (alembic, uvicorn, etc.)
COPY --from=builder /usr/local/bin/alembic \
                    /usr/local/bin/uvicorn \
                    /usr/local/bin/

# Copy application source
COPY --chown=appuser:appgroup . .

# Permissions
RUN chmod +x /app/entrypoint.sh && \
    mkdir -p /app/uploads/resumes && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# ---------------------------------------------------------------------------
# Stage 3: development — adds dev tools on top of runtime
# ---------------------------------------------------------------------------
FROM runtime AS development

USER root

RUN pip install --no-cache-dir watchfiles httpx pytest pytest-asyncio fakeredis

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
