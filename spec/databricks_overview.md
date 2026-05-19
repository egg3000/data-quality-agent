# Data Quality Agent — Databricks Deployment Specification

> This document is a self-contained specification for building the Data Quality Agent (DQA) targeting Databricks as the production deployment platform. It assumes the implementer is starting from scratch.

---

## 1. What This Is

A rules-based system for detecting and tracking data quality issues in ERP master data. The core concept:

- Each **rule** is a SQL `SELECT` query. If it returns zero rows, the data is clean. If it returns any rows, those rows are recorded as **errors**.
- An **AI agent** (LangGraph + a Databricks-hosted chat model) is the primary user interface. Analysts converse with it to investigate errors, draft new rules, and capture business-domain knowledge.
- A **knowledge base** (pgvector-backed semantic store) grows over time as the agent records what it learns from analysts, so future investigations have context.

The first dataset is SAP Material Master (MARA + MARC). The system is designed to generalize beyond that, but everything in this spec assumes that data shape as the starter.

---

## 2. Deployment Model

The production target is **Databricks**, deployed via **Databricks Asset Bundles**. Three Databricks resources back the system:

| Resource | Purpose |
|---|---|
| Databricks App (single app) | Hosts the FastAPI backend AND serves the React frontend as static assets from the same process |
| Lakebase (managed Postgres) | App database — rules, errors, runs, knowledge base, conversations. Has `pgvector` enabled. |
| Databricks Job | Scheduled trigger that calls the app's `/runs` endpoint on a cron (e.g. nightly batch execution of active rules) |

The ERP data the rules run against is **external to the app's storage** — Databricks SQL warehouse over Unity Catalog tables. The data source is reached through SQLAlchemy with the `databricks` dialect; credentials come from the Databricks SDK's unified auth (see Section 5.7), not from a connection string.

### 2.1 Single-App Pattern (Frontend + Backend Together)

The React frontend is built to static files (`npm run build` → `dist/`) and copied into the Python app image. FastAPI serves them in production:

- `/api/*` → FastAPI routes (rules, runs, errors, knowledge, chat)
- `/*` → static assets from `dist/`, with a fallback to `index.html` for client-side routing

In local dev the static mount is disabled and Vite runs as a separate process (see Section 9) so the frontend keeps HMR; the static-file path is exercised only in real bundle deploys.

Benefits at this scope: one deployment artifact, one compute unit, no CORS, one auth flow (Databricks Apps handles user identity at the edge), and a single asset bundle. The frontend and backend ship together — accepted tradeoff.

### 2.2 LLM Access — Databricks Model Serving, Not a Second App

The agent itself runs inside the FastAPI process. LLM calls go out to **Databricks Model Serving endpoints**:

- **Foundation Model APIs** (e.g. Llama, DBRX, GTE embeddings) — pay-per-token, no infra to manage.
- **External Model endpoints** — Databricks-hosted proxy to Anthropic, OpenAI, etc. Keeps third-party keys inside Databricks secrets rather than in app env.

This is *not* "deploy the backend as a Model Serving endpoint." Model Serving is a poor fit for a multi-route CRUD API with persistent DB state. The serving layer exists where it belongs: behind the LLM call.

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| App database | Lakebase (managed PostgreSQL) + `pgvector` extension |
| ERP data source | Databricks SQL warehouse over Unity Catalog (SQLAlchemy `databricks` dialect) |
| API / Agent | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), LangGraph, LangChain |
| LLM | Databricks Model Serving (`ChatDatabricks` from `langchain-databricks`) |
| Embeddings | Databricks Foundation Model embeddings (`DatabricksEmbeddings`) |
| Frontend | React 18, TypeScript (strict), built with Vite |
| Local dev | Docker container that mimics the Databricks App runtime; talks to remote Databricks services (no local Postgres, no local model) |
| Production deployment | Databricks Asset Bundles (`databricks bundle deploy`) |
| Production scheduling | Databricks Jobs (cron → HTTP call to `/api/runs`) |

---

## 4. Project Structure

```
CLAUDE.md
README.md
databricks.yml                 # Asset bundle root — environments, variables, includes
resources/                     # Bundle resource definitions
  app.yml                      # Databricks App (the FastAPI+React process)
  job.yml                      # Scheduled job that hits /api/runs
  lakebase.yml                 # Lakebase instance + database
app.yaml                       # Databricks App runtime config (command, env, ports)
docker-compose.dev.yml         # Local dev — FastAPI container + Vite; remote Databricks services
.env.example
spec/
  00_overview.md
  databricks_overview.md       # (this file)
  diagrams/
    01_c4_architecture.mermaid
    02_er_schema.mermaid
    03_rules_execution_flow.mermaid
    04_agent_interaction.mermaid
    05_agent_tools.mermaid
test_data/                     # SAP MARA/MARC seed with intentional DQ issues
  01_ddl.sql                   # Databricks-compatible DDL (Delta tables in UC)
  02_seed_data.sql             # Databricks-compatible INSERTs
api/
  Dockerfile                   # Used both for local dev container and the App build context
  pyproject.toml               # or requirements.txt
  main.py                      # FastAPI app — mounts /api router; static mount is prod-only
  routers/
    rules.py
    runs.py
    errors.py
    knowledge.py
    chat.py
  middleware/
    auth.py                    # Reads Apps-injected identity headers (or dev shim — see 5.7 / 9.3)
  services/
    rules_executor.py          # Runs rule SQL against the data source
    agent.py                   # LangGraph agent definition + tool wiring
    model.py                   # Provider factory: chat model + embeddings model
    embeddings.py              # pgvector read/write helpers
  models/                      # SQLAlchemy ORM
  db/
    session.py                 # SDK-based Lakebase engine factory with token refresh
    migrations/                # Alembic — runs against Lakebase in every environment
  static/                      # Frontend build output is copied here at App build time (prod)
frontend/
  package.json
  vite.config.ts               # Dev proxy: /api → http://localhost:8000
  src/
    components/
      Dashboard/
      Chat/
      Rules/
      Knowledge/
    api/                       # Typed fetch wrappers
    types/                     # Shared API response shapes
```

### 4.1 Asset Bundle Layout

`databricks.yml` is the bundle root. It defines per-environment targets (`dev`, `prod`) and includes the resource files under `resources/`. The `dev` target uses `mode: development`, which automatically prefixes resource names with the deploying user — so multiple developers can each run `databricks bundle deploy --target dev` without colliding.

The app resource references `app.yaml` for its runtime config. The job resource defines a cron schedule that POSTs to the app's `/api/runs` endpoint. The Lakebase resource declares the managed Postgres instance and database name; `pgvector` is enabled via the first Alembic migration, not via the bundle.

---

## 5. Key Architectural Decisions

### 5.1 Data Source Abstraction

`rules_executor.py` builds a SQLAlchemy engine that targets the ERP data source. The engine is constructed in one place; everything else uses the resulting session. The connection identifier (warehouse `http_path`, catalog, schema) comes from `DATA_SOURCE_URL`; the credentials come from the Databricks SDK auth path (see 5.7), not from the URL.

```
DATA_SOURCE_URL=databricks://<workspace-host>/?http_path=/sql/1.0/warehouses/<id>&catalog=<catalog>&schema=<schema>
```

The same URL shape is used in dev and prod — the only thing that differs is which catalog/schema and which warehouse it points at.

### 5.2 Two Logical Databases

Keep these clearly separated in code:

- **App DB** — Lakebase. Stores DQA application tables only. The connection is built dynamically by `db/session.py` using the SDK; there is no static URL with embedded credentials.
- **Data Source** — Databricks SQL warehouse over UC. Where ERP data lives. Read-only from DQA's perspective.

The two are never assumed to be the same database, and rule SQL must run only against the data source.

### 5.3 Single-App FastAPI + Static Frontend

`api/main.py` mounts the API router under `/api` unconditionally. The static-file mount and SPA fallback are gated on `ENV != "development"` so that local dev does not require a frontend build artifact inside the container:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings

app = FastAPI()
app.include_router(api_router, prefix="/api")

if settings.env != "development":
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse("static/index.html")
```

The frontend build is produced during the Databricks App build step and lives in `api/static/` at runtime in prod. In dev, Vite serves the frontend on a separate port and proxies `/api` to the container (see 9.2).

### 5.4 Agent — LangGraph, Model-Agnostic

The agent uses LangGraph for the ReAct loop and LangChain for the model abstraction. The model is never instantiated directly in `agent.py` — always via `services/model.py`:

```python
# services/model.py
from app.core.config import settings

def get_chat_model():
    if settings.model_provider == "databricks":
        from langchain_databricks import ChatDatabricks
        return ChatDatabricks(endpoint=settings.model_name)
    if settings.model_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=settings.model_name)
    if settings.model_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.model_name)
    raise ValueError(f"Unsupported MODEL_PROVIDER: {settings.model_provider}")

def get_embeddings_model():
    if settings.embeddings_provider == "databricks":
        from langchain_databricks import DatabricksEmbeddings
        return DatabricksEmbeddings(endpoint=settings.embeddings_model_name)
    if settings.embeddings_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings()
    raise ValueError(f"Unsupported EMBEDDINGS_PROVIDER: {settings.embeddings_provider}")
```

`MODEL_PROVIDER=databricks` is the default in every environment, including local dev — the local container calls Databricks Model Serving over the network. `anthropic` and `openai` exist as escape hatches for offline experimentation only and should not be used in normal dev. Tools are defined with the `@tool` decorator from `langchain_core.tools`. The agent graph is built with `langgraph.prebuilt.create_react_agent` unless custom state handling demands a `StateGraph`.

See `spec/diagrams/04_agent_interaction.mermaid` and `05_agent_tools.mermaid` for the full flow and tool inventory.

### 5.5 Knowledge Base — pgvector on Lakebase

Knowledge entries live in `knowledge_entries` with a `vector` column. Embeddings are generated via the abstraction in `services/model.py`. Semantic search uses the `<=>` (cosine distance) operator. **No separate vector database** — Lakebase + pgvector is sufficient and keeps everything in one Postgres instance.

### 5.6 Scheduling

- **Local dev:** no scheduler. Rules are triggered manually by hitting `/api/runs` (the local container, which then queries the remote Databricks data source).
- **Production:** A Databricks Job (defined in `resources/job.yml`) runs on cron and POSTs to `/api/runs` to execute all active rules. The job authenticates as a service principal.

### 5.7 Authentication — SDK Unified Auth Everywhere

The system standardizes on **Databricks SDK unified auth** for all app-to-Databricks-service calls. Application code never branches on environment; it just calls the SDK and lets the SDK pick the credential source.

- **User → App:** In prod, Databricks Apps inject identity at the edge as `X-Forwarded-Email` / `X-Forwarded-User` headers. The middleware in `api/middleware/auth.py` reads these and attaches the user to request state. In dev, the same middleware fakes the headers from `DEV_USER_EMAIL` — **guarded by `ENV == "development"`**, and MUST refuse to run otherwise. This is a security-critical guardrail.
- **App → Lakebase:** Lakebase uses **short-lived OAuth tokens**, not static passwords. `db/session.py` mints a connection credential via the Databricks SDK and refreshes it before expiry. There is no static `APP_DB_URL` with embedded credentials anywhere in the system.
- **App → ERP data source:** SQLAlchemy `databricks` dialect, authenticated through the same SDK auth path. `DATA_SOURCE_URL` carries the warehouse identifier but not credentials.
- **App → Model Serving:** `ChatDatabricks` / `DatabricksEmbeddings` from `langchain-databricks` delegate to SDK unified auth.

Credential source per environment:

| Environment | SDK auth source |
|---|---|
| Production (Databricks App) | App-injected service principal — automatic, no config needed |
| Local dev container | `~/.databrickscfg` profile, mounted read-only into the container |
| CI / bundle deploy | Service principal OAuth via env vars (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`) |

### 5.8 Dev/Prod Parity — The "App-Mimic" Local Container

The local development environment is **not** a replica of Databricks. It is a faithful stand-in for the App container alone, with everything stateful (Lakebase, SQL warehouse, Model Serving) consumed remotely from a developer-scoped tier in the same workspace. The same Dockerfile that defines the local container is the build context the Databricks App uses in prod, so the only differences between local and prod runtimes are:

1. **Credential source** — `databrickscfg` mount in dev vs. App-injected service principal in prod (the application code is identical because both flow through SDK unified auth).
2. **User identity** — dev middleware shim vs. App-injected `X-Forwarded-*` headers.
3. **Static-file mount** — disabled in dev (Vite runs separately) vs. enabled in prod.
4. **Hot reload** — `uvicorn --reload` plus a source-code bind mount in dev.

Everything else — Python version, dependencies, command, port, env-var names — matches. See Section 9 for the full local setup.

---

## 6. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ENV` | Yes | `development` or `production`. Gates dev-only middlewares and the static-file mount. |
| `LAKEBASE_INSTANCE` | Yes | Lakebase instance name. The SDK uses this to mint connection tokens. |
| `LAKEBASE_DATABASE` | Yes | Database name within the Lakebase instance. |
| `DATA_SOURCE_URL` | Yes | SQLAlchemy URL identifying the ERP data warehouse + catalog + schema. No credentials in the URL. |
| `MODEL_PROVIDER` | No | `databricks` (default). `anthropic` / `openai` are offline-only escape hatches. |
| `MODEL_NAME` | No | Model Serving endpoint name (e.g. `databricks-meta-llama-3-1-405b-instruct`). |
| `EMBEDDINGS_PROVIDER` | No | `databricks` (default). `openai` available as an alternative. |
| `EMBEDDINGS_MODEL_NAME` | No | Embeddings endpoint name (e.g. `databricks-gte-large-en`). |
| `DATABRICKS_CONFIG_PROFILE` | Dev only | `databrickscfg` profile name for SDK auth (typically `DEFAULT`). Not used in prod — the App injects credentials. |
| `DEV_USER_EMAIL` | Dev only | Identity used by the dev auth middleware when `ENV=development`. Ignored otherwise. |
| `ANTHROPIC_API_KEY` | No | Required only when `MODEL_PROVIDER=anthropic` (offline dev). |
| `OPENAI_API_KEY` | No | Required only when `MODEL_PROVIDER=openai` or `EMBEDDINGS_PROVIDER=openai`. |

Secrets in production come from Databricks Secret Scopes and are surfaced to the app via `app.yaml`. There are deliberately no secret env vars for Lakebase or the data source — those credentials flow through SDK auth, not through env vars.

---

## 7. Rule Schema

The `rules` table is the core of the system. Every rule has:

- `sql_query` — a `SELECT` statement that returns rows only when a data problem exists. Zero rows = no error; any rows = errors.
- `category` — one of: `completeness`, `validity`, `consistency`, `uniqueness`, `referential_integrity`, `timeliness`, `orphans`, `business_rules`.
- `severity` — integer: `1` = info, `2` = warning, `3` = error, `4` = critical.
- `is_active` — only active rules run in a batch execution.

`rule_errors.error_data` stores the raw row returned by the rule SQL as JSONB. Rules should `SELECT` enough columns to make the error record meaningful (e.g. include `matnr`, `werks`, the offending field value).

Rule SQL conventions:
- Always alias the primary key column so the error record is identifiable.
- Rule SQL targets the ERP data source (Databricks SQL warehouse), never the app DB.
- Rule SQL must be valid Databricks SQL (Spark SQL dialect). It will run against UC tables in both dev and prod, so dialect drift between environments is not a concern.

---

## 8. Test Data

SAP Material Master test data (MARA + MARC) lives in `test_data/`. It is loaded into a per-developer Unity Catalog schema once (e.g. `dqa_dev.<your_name>.mara`), not into the local container. The seed contains intentional data quality issues, each annotated with a `[DQ-ISSUE: CATEGORY]` comment — these are the targets for the starter rule set. The implementer must write at least one rule per category that catches one of these known issues.

The SQL files use Databricks SQL (Delta tables in UC). Load them via the Databricks SQL editor, a notebook, or the CLI:

```bash
databricks sql query --warehouse-id <id> --file test_data/01_ddl.sql
databricks sql query --warehouse-id <id> --file test_data/02_seed_data.sql
```

In production this seed is not loaded — the ERP data source is the real warehouse populated by upstream pipelines.

---

## 9. Local Development

Local dev does **not** replicate Databricks services. A local container is a faithful stand-in for the Databricks App runtime, and talks over the network to real Databricks resources (Lakebase, SQL warehouse, Model Serving) in a developer-scoped dev tier. The container is the same FastAPI process that runs in production; only its credential source and a couple of dev-only middlewares differ.

### 9.1 What runs where

| Component | Local | Databricks (dev tier) |
|---|---|---|
| FastAPI process | Docker container with hot reload | (Same image deployed to a `dev` App when verifying Apps-platform behavior) |
| Vite dev server | Host or sibling container; proxies `/api` to the FastAPI container | — |
| App database | — | Lakebase (per-developer database or schema) |
| ERP data source | — | Databricks SQL warehouse + per-developer UC schema |
| LLM | — | Databricks Model Serving endpoint (shared or per-developer) |
| Embeddings | — | Databricks Foundation Model embeddings endpoint |
| Scheduled job | — (trigger `/api/runs` manually) | Databricks Job (only on real dev-target bundle deploys) |

There is no local Postgres, no local model, no local warehouse. Working on the project requires network access to the workspace.

### 9.2 Compose file (`docker-compose.dev.yml`)

```yaml
services:
  api:
    build: ./api
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./api:/app
      - ~/.databrickscfg:/root/.databrickscfg:ro
    environment:
      ENV: development
      DATABRICKS_CONFIG_PROFILE: DEFAULT
      LAKEBASE_INSTANCE: ${LAKEBASE_INSTANCE}
      LAKEBASE_DATABASE: ${LAKEBASE_DATABASE}
      DATA_SOURCE_URL: ${DATA_SOURCE_URL}
      MODEL_PROVIDER: databricks
      MODEL_NAME: ${MODEL_SERVING_ENDPOINT}
      EMBEDDINGS_PROVIDER: databricks
      EMBEDDINGS_MODEL_NAME: ${EMBEDDINGS_ENDPOINT}
      DEV_USER_EMAIL: ${DEV_USER_EMAIL}
    ports: ["8000:8000"]

  frontend:
    image: node:20
    working_dir: /app
    command: npm run dev -- --host 0.0.0.0
    volumes: ["./frontend:/app"]
    environment:
      VITE_API_BASE_URL: http://localhost:8000
    ports: ["3000:3000"]
```

### 9.3 Auth wiring

- **Container → Databricks services (Lakebase, warehouse, Model Serving):** the Databricks SDK's unified auth picks up the mounted `~/.databrickscfg` profile and uses the developer's personal credentials. In prod, the same code path picks up the App's injected service principal. No branches in application code.
- **User → App:** the auth middleware in `api/middleware/auth.py` reads `X-Forwarded-Email` / `X-Forwarded-User` in prod. In dev, when `ENV=development`, it fakes these from `DEV_USER_EMAIL`. The dev branch must refuse to run when `ENV != "development"`.

### 9.4 Inner loop

- **Backend edit:** ~1s, via `uvicorn --reload`.
- **Frontend edit:** ~100ms, via Vite HMR.
- **Bundle deploy (`databricks bundle deploy --target dev`):** only when verifying Apps-platform behavior — `app.yaml` changes, scheduled job changes, real edge-injected identity headers, the production static-file mount path, secret binding. Typically a few times per day, not per change.

### 9.5 First-time setup

1. `databricks auth login --host https://<workspace>...` — populates `~/.databrickscfg` on the host.
2. `databricks bundle deploy --target dev` — provisions the per-developer dev resources (Lakebase database/schema, UC schema for ERP data, references to shared Model Serving endpoints). Bundle `mode: development` namespaces these per user.
3. Load test data into the dev UC schema (see Section 8).
4. `cp .env.example .env` and fill in `LAKEBASE_INSTANCE`, `LAKEBASE_DATABASE`, `DATA_SOURCE_URL`, `MODEL_SERVING_ENDPOINT`, `EMBEDDINGS_ENDPOINT`, `DEV_USER_EMAIL`.
5. `docker compose -f docker-compose.dev.yml up --build`.
6. Frontend: http://localhost:3000 — API: http://localhost:8000/docs.

### 9.6 Known limitations

- Requires workspace network reachability. No airport coding.
- Multiple developers sharing one Lakebase instance need per-developer schemas/DBs to avoid clobbering. The bundle's `dev` target namespaces by user; do not bypass it.
- SQL warehouse cold start on first query is ~30s. Keep a small warehouse warm during dev hours or accept the latency.
- Lakebase, warehouse compute, and Model Serving invocations are billed during dev. Use small warehouses and modest model sizes for the dev tier.

---

## 10. Production Deployment

```bash
# Authenticate once
databricks auth login --host https://<workspace>.cloud.databricks.com

# Deploy
databricks bundle validate
databricks bundle deploy --target prod
```

The bundle:
1. Provisions/updates the Lakebase instance.
2. Runs Alembic migrations against Lakebase (enabling `pgvector` is the first migration).
3. Builds the frontend (`npm ci && npm run build`) and copies the output into the app build context.
4. Builds and deploys the Databricks App with `app.yaml` as its runtime config.
5. Creates/updates the scheduled Job that calls `/api/runs`.

App URL: `https://<app-name>-<workspace-id>.<region>.databricksapps.com`.

---

## 11. Code Conventions

- **Python:** async/await throughout FastAPI routes and services. SQLAlchemy 2.0 async sessions. No sync DB calls inside request handlers.
- **TypeScript:** strict mode on. No `any` types. All API response shapes defined in `src/types/`.
- **SQL rules:** always alias the primary key column so error records are identifiable. Rule SQL must be valid Databricks SQL.
- **Error handling:** API errors return `{"detail": "..."}` with appropriate HTTP status codes. Agent tool errors return a structured error result rather than raising — the agent decides how to handle them.
- **Migrations:** Alembic for all schema changes to the app DB. Migrations run in every environment, including the first time a dev environment is provisioned.
- **No static DB credentials.** Lakebase and warehouse credentials always flow through Databricks SDK unified auth. Never put a password in an env var or a connection string.
- **No direct model instantiation outside `services/model.py`.** Always go through the factory.
- **Dev-only code paths must be guarded by `ENV == "development"`** and must refuse to run otherwise. The auth shim is the most security-critical example.

---

## 12. Out of Scope for v1

- Multi-tenancy. The app assumes a single workspace and a single ERP dataset.
- Row-level security on rule results. All app users see all errors.
- Streaming agent responses to the frontend. v1 uses request/response chat; streaming is a later enhancement.
- Automated rule generation from natural language alone. The agent can *propose* rule SQL, but a human approves and activates it.
- A fully offline dev mode. `anthropic` / `openai` model providers exist as escape hatches but no first-class offline story is supported — dev requires workspace network access.
