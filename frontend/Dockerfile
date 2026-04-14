# =============================================================================
# TalentBridge — Frontend Dockerfile (multi-stage)
# Stage: deps        → install node_modules
# Stage: builder     → next build (standalone output)
# Stage: runtime     → minimal image running next start
# Stage: development → deps + next dev (used by docker-compose.override.yml)
# =============================================================================

ARG NODE_VERSION=20-alpine

# ---------------------------------------------------------------------------
# Stage 1: deps — install all node_modules
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION} AS deps

WORKDIR /app

# Copy manifests first (cache layer)
COPY package.json package-lock.json* ./

RUN npm install

# ---------------------------------------------------------------------------
# Stage 2: builder — produce standalone Next.js build
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION} AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# next build reads NEXT_PUBLIC_* at build time — pass them via ARG/ENV
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 3: runtime — copy standalone output, non-root user
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION} AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy Next.js standalone output
COPY --from=builder --chown=appuser:appgroup /app/.next/standalone ./
COPY --from=builder --chown=appuser:appgroup /app/.next/static ./.next/static
COPY --from=builder --chown=appuser:appgroup /app/public ./public

USER appuser

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]

# ---------------------------------------------------------------------------
# Stage 4: development — full deps + hot reload
# ---------------------------------------------------------------------------
FROM deps AS development

WORKDIR /app

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

CMD ["npm", "run", "dev"]
