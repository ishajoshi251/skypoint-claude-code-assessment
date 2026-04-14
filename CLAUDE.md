# CLAUDE.md — Project Specification & Working Agreement

This file is the single source of truth for Claude Code while building this project. Read it fully before generating, modifying, or scaffolding any code. Re-read the relevant sections before each new feature.

---

## 1. Project Overview

**Product name (working):** TalentBridge — a modern, opinionated job portal in the spirit of Naukri / LinkedIn Jobs, but built around *intelligent matching* rather than keyword spam.

**Why this exists:** This is a take-home assessment for Skypoint.ai (Full-Stack Engineer role). The submission is judged not just on "does it work" but on:

- Code quality & organisation
- Best practices (env vars, separation of concerns, version control hygiene)
- Security (auth, authz, validation, safe data handling)
- Docker & DevOps (single-command startup)
- Documentation (README clarity)
- Testing
- Judicious use of Claude Code

**The assessor will clone the repo on a fresh machine and run `docker compose up --build`. If it doesn't come up cleanly with that one command, we fail before the code is even read.** Treat this as a hard constraint.

---

## 2. Hard Requirements (from the brief — non-negotiable)

1. **Frontend UI** — interactive, self-explanatory.
2. **Backend API / service layer.**
3. **Database** — containerised, with persistent volume.
4. **Authentication with at least two distinct roles**: `HR` (recruiter) and `CANDIDATE` (job-seeker).
5. **Dockerised end-to-end** via `docker compose`. One command. No manual setup beyond what's in the README.
6. **Env vars for all config and secrets.** No hardcoded credentials. A committed `.env.example` and a gitignored `.env`.
7. **Input validation on both frontend and backend.**
8. **Error handling throughout the stack.**
9. **At least basic unit / integration tests.**
10. **Clean commit history** — logical progression, not one "initial dump" commit.
11. **`.gitignore`** for `node_modules`, `__pycache__`, `.venv`, `.env`, build artifacts, IDE files (`.vscode`, `.idea`).
12. **README** covering: overview, architecture, how to run, test credentials, feature walkthrough, tech stack, known limitations.

---

## 3. Tech Stack (locked-in)

Pick this stack and stick with it. Don't drift mid-project.

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 14** (App Router) + **TypeScript** + **Tailwind CSS** + **shadcn/ui** + **TanStack Query** + **Zustand** (light client state) + **React Hook Form** + **Zod** | Modern, batteries-included, type-safe end-to-end with Zod schemas shared mentally with backend Pydantic |
| Backend | **FastAPI** (Python 3.11) + **SQLAlchemy 2.0** + **Pydantic v2** + **Alembic** (migrations) | Clean async API, automatic OpenAPI docs at `/docs`, excellent for the NLP/matching pieces |
| Database | **PostgreSQL 16** with **pgvector** extension | Relational integrity + vector similarity search for the smart-matching feature |
| Cache / rate-limit | **Redis 7** | Session/refresh-token store, rate limiting, background job queue |
| Background jobs | **RQ** (Redis Queue) or FastAPI `BackgroundTasks` for v1 | Resume parsing, bulk email send, embedding generation |
| Auth | **JWT** (access + refresh) via `python-jose`, passwords hashed with **bcrypt** (`passlib`) | Stateless API, refresh rotation |
| Email (dev) | **MailHog** (containerised SMTP catcher at `localhost:8025`) | Assessor can see "sent" emails without real SMTP |
| Resume parsing | `pdfplumber`, `python-docx`, `spaCy` (`en_core_web_sm`) | Extract text + named entities (skills, orgs, dates) |
| Matching engine | **Hybrid**: TF-IDF (scikit-learn) for keyword score + **sentence-transformers** (`all-MiniLM-L6-v2`) for semantic score, blended | Explainable + smart |
| Frontend tests | **Vitest** + **React Testing Library** | Fast |
| Backend tests | **pytest** + **pytest-asyncio** + **httpx** AsyncClient | Standard |
| Lint/format | **ruff** + **black** (Python), **eslint** + **prettier** (TS) | Pre-commit hook ideal but not required |

**Do not** add: GraphQL, microservices, Kafka, Kubernetes, a separate auth service, an ORM other than SQLAlchemy, or any "enterprise" pattern that doesn't earn its keep. Simplicity wins points here.

---

## 4. Repository Layout

```
talentbridge/
├── README.md                     # see §10 for required contents
├── CLAUDE.md                     # this file
├── docker-compose.yml            # orchestrates: web, api, db, redis, mailhog
├── docker-compose.override.yml   # dev-only overrides (hot reload, exposed ports)
├── .env.example                  # committed, every var documented
├── .gitignore
├── .dockerignore
├── docs/
│   ├── architecture.md           # diagram + dataflow
│   └── api.md                    # link to /docs (OpenAPI) + auth flow notes
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/                  # migrations
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, middleware, routers
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic Settings, reads env
│   │   │   ├── security.py       # JWT, password hashing
│   │   │   ├── deps.py           # FastAPI dependencies (get_db, get_current_user, require_role)
│   │   │   └── exceptions.py     # custom exceptions + global handlers
│   │   ├── db/
│   │   │   ├── base.py           # SQLAlchemy Base
│   │   │   ├── session.py        # async engine + sessionmaker
│   │   │   └── seed.py           # seed test users + sample jobs
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── candidate_profile.py
│   │   │   ├── company.py
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   ├── resume.py
│   │   │   └── invite.py
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── api/v1/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── jobs.py
│   │   │   │   ├── applications.py
│   │   │   │   ├── candidates.py     # HR-only search endpoints
│   │   │   │   ├── matching.py       # JD → ranked candidates
│   │   │   │   ├── resumes.py        # upload + parse
│   │   │   │   └── analytics.py      # HR dashboard
│   │   │   └── router.py
│   │   ├── services/             # business logic, no FastAPI imports
│   │   │   ├── auth_service.py
│   │   │   ├── matching_service.py
│   │   │   ├── resume_parser.py
│   │   │   ├── email_service.py
│   │   │   └── embedding_service.py
│   │   └── utils/
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_jobs.py
│       ├── test_matching.py
│       └── test_rbac.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.mjs
    ├── tailwind.config.ts
    ├── src/
    │   ├── app/
    │   │   ├── (auth)/login, register
    │   │   ├── (candidate)/dashboard, jobs, applications, profile
    │   │   ├── (hr)/dashboard, jobs/new, candidates, analytics
    │   │   └── layout.tsx
    │   ├── components/
    │   │   ├── ui/               # shadcn primitives
    │   │   ├── jobs/
    │   │   ├── candidates/
    │   │   └── shared/
    │   ├── lib/
    │   │   ├── api.ts            # typed axios/fetch client
    │   │   ├── auth.ts           # token storage, refresh logic
    │   │   └── schemas.ts        # zod schemas
    │   ├── hooks/
    │   └── stores/
    └── tests/
```

**Rule:** Keep `services/` framework-agnostic. Routes are thin: validate → call service → return schema. This makes testing trivial.

---

## 5. Data Model (essential entities)

- **User** — `id`, `email` (unique), `password_hash`, `role` (`HR` | `CANDIDATE`), `is_active`, `created_at`.
- **CandidateProfile** — 1:1 with User where role=CANDIDATE. `full_name`, `headline`, `location`, `years_experience`, `current_salary`, `expected_salary`, `notice_period_days`, `skills` (array), `bio`, `resume_id`, `embedding` (vector, 384 dims).
- **Company** — `id`, `name`, `website`, `description`, `created_by_user_id`.
- **Job** — `id`, `company_id`, `posted_by_user_id`, `title`, `description`, `required_skills` (array), `min_experience`, `max_experience`, `min_salary`, `max_salary`, `location`, `employment_type`, `embedding` (vector), `status` (`OPEN`|`CLOSED`), `created_at`.
- **Application** — `id`, `job_id`, `candidate_id`, `status` (`APPLIED`|`SHORTLISTED`|`INTERVIEW`|`OFFERED`|`HIRED`|`REJECTED`), `cover_letter`, `match_score`, `created_at`. Unique on `(job_id, candidate_id)`.
- **Resume** — `id`, `candidate_id`, `file_path`, `parsed_text`, `parsed_skills`, `parsed_experience_years`.
- **Invite** — `id`, `hr_user_id`, `candidate_id`, `job_id`, `message`, `sent_at`, `status`.

Use Alembic from day one. No `Base.metadata.create_all` shortcuts in production code paths (seed script is fine).

---

## 6. Innovative Features (this is where we differentiate)

### 6.1 HR Features

1. **JD-Powered Smart Search (flagship feature)**
   HR pastes a job description (or fills structured params: must-have skills, experience range, salary band, location, notice period). The matcher returns a **ranked candidate list** with:
   - **Match score** (0–100), broken down into: skill overlap %, semantic similarity %, experience fit, salary fit, location fit.
   - **Why this candidate** — short explanation listing matched skills + missing skills.
   - Filter chips to refine (toggle "must have AWS", "willing to relocate", etc).

2. **Bulk Personalised Invites**
   From the ranked list, select N candidates → click "Invite to apply" → backend generates a per-candidate personalised email (templated, mentions matched skills) → queued via MailHog. Track open/response status (status field on Invite).

3. **AI-Assisted JD Writer**
   HR types a rough title + 3 bullet points → backend (can use a simple template engine + skill suggestion from existing job corpus; LLM optional and gated behind env var) drafts a polished JD.

4. **Pipeline Kanban Board**
   Drag-and-drop candidates across stages: Applied → Shortlisted → Interview → Offered → Hired/Rejected. Status changes are auditable.

5. **Analytics Dashboard**
   Per-job funnel (views → applications → shortlisted → hired), time-to-hire, top sources of candidates, skill demand heatmap across all open jobs.

6. **Saved Searches with Alerts**
   Save a JD search → get notified (in-app badge + MailHog email) when a new candidate matching ≥80% signs up.

### 6.2 Candidate Features

1. **Match Score on every Job Card**
   Every job in the listing shows a personalised "X% match" badge based on the candidate's profile + resume embedding. Click to see breakdown.

2. **Smart Recommendations Feed**
   Home page is "Jobs picked for you" — top 10 by match score, refreshed when profile or resume updates.

3. **Resume Upload + Auto-Profile Fill**
   Upload PDF/DOCX → backend parses → pre-fills skills, experience years, past companies. Candidate confirms/edits. Re-uploading triggers re-embedding.

4. **Skill Gap Insight**
   For any job, show "You're missing: Kubernetes, GraphQL" with a hint to add to profile if they actually have it, or suggested learning topics.

5. **Application Tracker**
   Timeline view per application: Applied → Viewed by HR → Shortlisted → Interview scheduled → Outcome.

6. **Profile Completeness Meter**
   Gamified % bar — "Add a headline (+10%), upload a resume (+25%)…" — drives engagement and improves match quality.

7. **Salary Insights**
   For any role/location combo, show min/median/max from open jobs in the system (no external data needed).

**Scope discipline:** Build 6.1.1, 6.1.2, 6.1.4, 6.1.5 and 6.2.1, 6.2.2, 6.2.3, 6.2.5, 6.2.6 as **must-ship**. Treat the rest as stretch — only build if core is solid and tested. The README must list anything cut under "Known Limitations" honestly.

---

## 7. Frontend Principles

The brief says "interactive and self-explanatory". Interpret that as:

- **No empty states without guidance.** Every empty list has an illustration + CTA ("No applications yet — browse jobs").
- **Toasts** for every mutation (success/error) via `sonner`.
- **Skeleton loaders**, not spinners, on data fetches.
- **Inline validation** with React Hook Form + Zod. Errors appear on blur, not on submit-only.
- **Optimistic updates** for low-risk actions (saving a job, toggling status).
- **Keyboard accessible** — focus states visible, modals trap focus, escape closes them.
- **Match-score visualisations** — use a small radial/segmented bar (Recharts or hand-rolled SVG), not just a number.
- **Role-aware navigation.** HR and Candidate see entirely different shells. Don't try to cram both into one nav.
- **Dark mode** via Tailwind `dark:` classes — cheap to add, looks polished.
- **Mobile-responsive** at minimum — assessor may open on a phone.

Use shadcn/ui as the component base. Don't reinvent buttons, dialogs, dropdowns. Customise tokens in `tailwind.config.ts` so it doesn't look like every other shadcn site — pick a distinctive accent colour.

---

## 8. Security Checklist (this is graded)

- [ ] Passwords hashed with bcrypt, cost ≥ 12. Never logged, never returned.
- [ ] JWT access tokens short-lived (15 min); refresh tokens (7 days) rotated on use, stored in **httpOnly + Secure + SameSite=Lax** cookies. Access token in memory (Zustand), not localStorage.
- [ ] CORS locked to the frontend origin (env-driven), not `*`.
- [ ] **RBAC enforced server-side** on every protected route via a `require_role(Role.HR)` dependency. Never trust the frontend role.
- [ ] Object-level authz: a candidate can only read/modify their own application; an HR can only manage jobs of their own company.
- [ ] All inputs validated by Pydantic (backend) and Zod (frontend). Lengths capped. File uploads: size limit, MIME sniff, extension check, store outside webroot (use a Docker volume).
- [ ] SQL via SQLAlchemy parameterised queries only — no f-string SQL.
- [ ] Rate limit auth endpoints (`slowapi` + Redis): e.g., 5 login attempts / 5 min / IP.
- [ ] Generic error messages on auth ("Invalid credentials") — no user enumeration.
- [ ] `.env` is gitignored. `.env.example` lists every required var with safe placeholders.
- [ ] Resume files served via authenticated endpoint, not directly from the volume.
- [ ] Security headers via middleware: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, basic CSP for the API responses.
- [ ] No secrets in commit history. If one slips in, rewrite history before pushing.

---

## 9. Docker & DevOps

**`docker-compose.yml` services:**

- `db` — `pgvector/pgvector:pg16`, named volume `pgdata`, healthcheck.
- `redis` — `redis:7-alpine`, healthcheck.
- `mailhog` — `mailhog/mailhog`, ports `1025` (SMTP) and `8025` (UI).
- `api` — built from `./backend`, depends_on `db` (healthy) and `redis` (healthy), runs alembic upgrade + seed on start, then uvicorn.
- `web` — built from `./frontend`, depends_on `api`, exposes `3000`.

**Rules:**

- Backend `Dockerfile` is multi-stage (builder + slim runtime). Non-root user. Pin Python base image by digest if possible.
- Frontend `Dockerfile` is multi-stage: deps → build → `next start` runtime (or `output: 'standalone'`).
- Use `.dockerignore` aggressively — don't ship `node_modules`, `.git`, `.env`, tests to the runtime image.
- `depends_on` uses `condition: service_healthy`.
- All inter-service comms by service name (`api`, `db`, `redis`), not `localhost`.
- Volumes: `pgdata` for Postgres, `resumes` for uploaded files.
- Default ports exposed on host: `3000` (web), `8000` (api), `8025` (mailhog UI). Document these in README.
- An entrypoint script in the api container runs: `alembic upgrade head` → `python -m app.db.seed` → `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Seed must be **idempotent** (use `INSERT … ON CONFLICT DO NOTHING` or equivalent).

---

## 10. README (assessor's first impression — make it count)

Required sections, in this order:

1. **Project Overview** — 2–3 lines on what TalentBridge is and the problem it solves.
2. **Architecture** — a Mermaid diagram in the README itself showing `Browser → Next.js → FastAPI → (Postgres + Redis + MailHog)`. Brief paragraph on each component's role.
3. **How to Run** —
   ```bash
   git clone <url>
   cd talentbridge
   cp .env.example .env       # default values work out of the box
   docker compose up --build
   ```
   Then list URLs:
   - Web: http://localhost:3000
   - API docs: http://localhost:8000/docs
   - MailHog: http://localhost:8025
4. **Test Credentials** — seeded on first boot:
   - HR — `hr@test.com` / `Hr@12345`
   - Candidate — `candidate@test.com` / `Candidate@12345`
5. **Feature Walkthrough** — split by role, with the user flow ("As HR, click *Find Candidates*, paste a JD, hit *Rank* — top matches appear with score breakdowns…").
6. **Tech Stack** — bulleted list with versions.
7. **Testing** — how to run `pytest` and `vitest` both inside Docker (`docker compose exec api pytest`) and locally.
8. **Project Structure** — short tree, link to `docs/architecture.md` for detail.
9. **Known Limitations** — be honest. Examples: "Email sending is captured by MailHog — not wired to a real SMTP provider", "Semantic embeddings computed on-demand, no batch reindex job", "No password reset flow".
10. **Claude Code Notes** — a short paragraph on how Claude Code was used (planning, scaffolding, refactors), and any tool feedback. The brief explicitly asks for this.

---

## 11. Testing Strategy

Don't aim for 100% — aim for *meaningful* coverage on the parts that matter.

**Backend (pytest):**
- Auth: register, login, refresh, wrong password, role enforcement.
- RBAC: candidate cannot hit HR-only endpoints (assert 403).
- Jobs CRUD: HR can create, candidate cannot.
- Applications: candidate can apply once, duplicate returns 409.
- Matching service: given a known profile and JD, score is in expected range.
- Use a separate test database (override `DATABASE_URL` via env in `conftest.py`), wrap each test in a transaction that rolls back.

**Frontend (vitest + RTL):**
- Login form validation (required, email format, password rules).
- JobCard renders match score correctly.
- Smart-search form submits with correct payload.

Aim for ~15–25 backend tests and ~5–10 frontend tests. Quality > quantity.

---

## 12. Git Hygiene

- One feature per commit (or small logical group). Conventional commits style: `feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`.
- Suggested commit progression (also doubles as a build order):
  1. `chore: scaffold monorepo, docker-compose, env example`
  2. `feat(api): user model, auth (register/login/refresh), RBAC dependency`
  3. `feat(api): jobs and applications CRUD with authz`
  4. `feat(api): resume upload + parser`
  5. `feat(api): embeddings + matching service`
  6. `feat(api): HR smart-search and bulk invite endpoints`
  7. `feat(web): auth pages, role-aware shell, token handling`
  8. `feat(web): candidate dashboard, job feed with match scores`
  9. `feat(web): HR dashboard, smart search UI, kanban`
  10. `feat(web): analytics dashboard`
  11. `test: backend auth + matching, frontend forms`
  12. `docs: README, architecture diagram, env example`
  13. `chore: seed data, polish, dark mode`

Push at least every 2–3 commits so the history is visible if anything goes wrong locally.

---

## 13. Working Agreement with Claude Code

When I ask you (Claude Code) to work on this project, follow these rules:

1. **Read this file first** in any new session before touching code. If you're unsure about a decision, refer back here rather than inventing.
2. **Ask before changing the stack.** If a library is missing or broken, propose an alternative — don't silently swap (e.g., don't replace FastAPI with Flask, don't drop pgvector for plain Postgres without telling me).
3. **Small, reviewable changes.** Don't rewrite five files when one will do. Show diffs, not full file dumps, when iterating.
4. **Run the tests after meaningful changes.** If something breaks, fix it before claiming done.
5. **Plan briefly before large tasks.** For anything spanning >2 files, write a 5-bullet plan, get my nod, then code.
6. **Surface assumptions.** If you assume a column name, an env var name, a port — say so in the response so I can correct early.
7. **Idempotency matters.** Migrations, seed scripts, Docker entrypoints — all must be safe to re-run.
8. **Don't generate filler.** No "this comprehensive solution leverages industry-leading…" — just code and tight prose.
9. **Security is not optional.** If I ask for a feature that would weaken the checklist in §8, push back.
10. **When in doubt about scope, default to shipping the must-haves in §6 well, not the stretch goals badly.**

---

## 14. Definition of Done (run this checklist before pushing the final commit)

- [ ] `docker compose down -v && docker compose up --build` brings everything up cleanly on a fresh checkout.
- [ ] Both seeded users can log in. HR sees HR shell, candidate sees candidate shell.
- [ ] Candidate can: complete profile, upload resume, see match-scored job feed, apply to a job, track application status.
- [ ] HR can: post a job, paste a JD into smart search, see ranked candidates with score breakdown, send bulk invites (visible in MailHog), move candidates across the pipeline kanban, view analytics dashboard.
- [ ] All endpoints under `/api/v1` documented in `/docs` (FastAPI auto-OpenAPI).
- [ ] `pytest` passes inside the api container. `vitest` passes inside the web container (or locally).
- [ ] No secrets in the repo. `.env` gitignored. `.env.example` complete.
- [ ] README walks through every required section (§10).
- [ ] Git history is clean and tells a story.
- [ ] Repo URL emailed to `avinash.selvan@skypointcloud.com` before 9 PM IST, 14 April.