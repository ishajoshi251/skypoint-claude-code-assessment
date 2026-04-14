# TalentBridge — Architecture

> Detailed diagram and dataflow. Linked from README.

## Component Roles

| Component | Role |
|---|---|
| **Next.js (web)** | SSR + client-side SPA; role-aware routing; Zustand for auth state; TanStack Query for server state |
| **FastAPI (api)** | RESTful JSON API; JWT auth; RBAC; background tasks |
| **PostgreSQL + pgvector** | Relational store; vector columns for profile/job embeddings |
| **Redis** | Refresh token store; rate-limit counters; RQ job queue |
| **MailHog** | Dev SMTP catcher; all outbound emails visible at :8025 |

## Request Lifecycle

```
Browser
  └─► Next.js (SSR/Client) :3000
        └─► FastAPI API :8000
              ├─► PostgreSQL :5432
              ├─► Redis :6379
              └─► MailHog SMTP :1025
```

## Auth Flow

1. `POST /api/v1/auth/login` → access token (15 min, JSON body) + refresh token (7 days, httpOnly cookie)
2. Client stores access token in Zustand (memory only, not localStorage)
3. On 401, client hits `POST /api/v1/auth/refresh` using the cookie — gets a new access token + rotated refresh cookie
4. Logout clears the cookie server-side (`POST /api/v1/auth/logout`)

## Matching Pipeline

```
Candidate profile → sentence-transformers → 384-dim embedding → pgvector column
Job description   → sentence-transformers → 384-dim embedding → pgvector column

Smart search:
  1. Vector cosine similarity (semantic score)
  2. TF-IDF skill overlap (keyword score)
  3. Structured fit: experience, salary, location, notice period
  4. Blend → 0–100 match score + explanation
```
