# VoxDesk

Multi-tenant AI voice receptionist SaaS. AI answers a business's inbound calls,
answers questions from its knowledge base (RAG), books appointments, transfers
to a human when needed, and stores transcripts, summaries and analytics —
all managed from a web dashboard.

**Every external provider (LLM, STT, TTS, telephony, voice engine, calendar,
CRM, storage) sits behind an interface with a fully functional mock**, so the
entire platform runs end-to-end with zero credentials. Swapping placeholder
env vars for production values activates real providers without code changes.

## Stack

| Layer | Tech |
|---|---|
| Dashboard | Next.js 15 + TypeScript + Tailwind (deploys to Vercel) |
| API | FastAPI (async, OpenAPI at `/docs`) |
| Database | PostgreSQL (SQLAlchemy 2 + Alembic migrations) |
| Cache/queue | Redis |
| Vector DB | Qdrant (with DB keyword fallback) |
| Voice engine | Dograh (self-hosted) — adapter behind `VoiceEngineProvider` |
| Telephony | Telnyx — adapter behind `TelephonyProvider` |
| STT / TTS / LLM | Whisper / Kokoro / Qwen — behind provider interfaces (mock by default) |

## Repository layout

```
apps/web            Next.js dashboard (auth, agents, calls, KB, analytics, settings)
apps/api            FastAPI backend
  app/providers     Provider interfaces + adapters (mock, telnyx, dograh, …)
  app/services      Business logic: RAG pipeline, voice conversation loop
  app/routers       REST endpoints (auth, orgs, agents, calls, documents, …)
  app/worker.py     Background worker (Redis-queued document ingestion)
  alembic/          Database migrations
  tests/            Pytest suite (runs on SQLite, no services needed)
packages/shared     Shared TypeScript API types
scripts/seed.py     Demo data seeder
docker-compose.yml  Postgres + Redis + Qdrant + API + worker
.github/workflows   CI (backend tests + frontend build)
```

## Quick start

```bash
cp .env.example .env

# 1. Backend + infrastructure (one command)
docker compose up --build
# API on http://localhost:8000 (OpenAPI docs at /docs)

# 2. Dashboard
cd apps/web
cp .env.local.example .env.local
npm install
npm run dev
# Dashboard on http://localhost:3000
```

Or run the API without Docker:

```bash
cd apps/api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head          # needs DATABASE_URL reachable
.venv/bin/uvicorn app.main:app --reload
```

Seed demo data (org, agent, knowledge doc, 3 sample calls):

```bash
cd apps/api && .venv/bin/python ../../scripts/seed.py
# login: demo@voxdesk.app / demo1234!
```

Run tests:

```bash
cd apps/api
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest tests
```

## How a call flows (Dograh workflow spec)

```
Caller → Telnyx → Dograh (audio loop) → webhook /webhooks/dograh
   → greeting → collect caller (name captured onto the call record)
   → STT → intent → RAG retrieval (Qdrant) → LLM (+ tool calls) → TTS reply
   → book_appointment → CalendarProvider + CRMProvider
     → optional hand-off: agent "transfer after booking" routes the caller
       to a human for conversion once they finalize
   → transfer_to_human → TelephonyProvider.transfer_call
   → call ended → summary + recording stored → analytics
```

Recordings: with a real engine, Dograh posts a `recording_url` on
`call.ended`; on mock providers the transcript is rendered to a playable WAV.
Either way `GET /calls/{id}/recording` serves it and the call page in the
dashboard has an audio player next to the transcript.

The same pipeline is runnable in-process without any provider via
`POST /calls/simulate` (also exposed as "Simulate a call" on the Calls page) —
this is the demo/acceptance path.

## Multi-tenancy & security

- Every org-owned row carries `organization_id`; all queries are scoped
  through the `TenantCtx` dependency — no cross-tenant access.
- JWT auth (email + password), RBAC roles: owner / admin / member.
- Audit log rows for every mutating action.
- Rate limiting on auth endpoints (Redis fixed-window).
- Soft deletes everywhere (`deleted_at`).
- Secrets only via environment variables; `.env.example` ships placeholders.

## Going to production (the only manual steps left)

1. Deploy `apps/web` to Vercel; set `NEXT_PUBLIC_API_URL`.
2. Host the backend (`docker compose up`) behind a reverse proxy with TLS.
3. Self-host Dograh, set `DOGRAH_URL` + `DOGRAH_API_KEY`, `VOICE_ENGINE=dograh`.
4. Add Telnyx credentials, set `TELEPHONY_PROVIDER=telnyx`, point the Telnyx
   webhook at `https://api.yourdomain.com/webhooks/telnyx`.
5. Point STT/TTS/LLM at real Whisper/Kokoro/Qwen endpoints and switch the
   `*_PROVIDER` env vars.
6. Replace `JWT_SECRET`, DB credentials, and configure DNS.
