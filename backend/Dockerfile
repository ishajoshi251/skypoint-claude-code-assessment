# =============================================================================
# TalentBridge — Backend Dockerfile (multi-stage)
# Stage: builder  → installs deps into a virtual env via uv (fast Rust resolver)
# Stage: runtime  → slim image, non-root user
# Stage: development → runtime + dev tools + reload
# =============================================================================

ARG PYTHON_VERSION=3.11-slim

# ---------------------------------------------------------------------------
# Stage 1: builder — install Python deps with uv
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS builder

WORKDIR /build

# System deps needed to compile native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv — fast Rust-based pip replacement that handles deep dep graphs
RUN pip install --upgrade pip uv

# Copy dependency spec first (layer cache)
COPY pyproject.toml ./

# Create venv and install production deps via uv
RUN python -m venv /build/.venv
ENV PATH="/build/.venv/bin:$PATH"
RUN uv pip install --no-cache ".[prod]"

# ---------------------------------------------------------------------------
# Stage 2: runtime — non-root, slim
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS runtime

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy the pre-built venv from builder
COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source
COPY --chown=appuser:appgroup . .

# Create upload dir and set ownership
RUN mkdir -p /app/uploads/resumes && chown -R appuser:appgroup /app/uploads

USER appuser

EXPOSE 8000

COPY --chown=appuser:appgroup entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# ---------------------------------------------------------------------------
# Stage 3: development — mounts source as volume, enables reload
# ---------------------------------------------------------------------------
FROM runtime AS development

USER root

ENV PATH="/app/.venv/bin:$PATH"
RUN pip install uv && \
    uv pip install --no-cache watchfiles httpx pytest pytest-asyncio fakeredis

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
