# Data Quality Agent

## What This Is

A rules-based system for detecting and tracking data quality issues in ERP master data. The core concept: each rule is a SQL query that, when it returns any rows, signals a data problem. An AI agent (Claude with tool use) serves as the primary interface — analysts chat with it to investigate errors, write new rules, and build a persistent knowledge base of business domain expertise over time.

Read the full specification before writing any code: `spec/00_overview.md`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 15 + pgvector extension |
| API / Agent | Python 3.11, FastAPI, SQLAlchemy, LangGraph, LangChain |
| Frontend | React 18, TypeScript |
| Containerization | Docker + Docker Compose |
| Production deployment | Databricks Apps (Databricks job scheduler handles scheduling) |

---

## Project Structure

```
CLAUDE.md
docker-compose.yml
spec/                        # Architecture diagrams and specification
  00_overview.md
  diagrams/
    01_c4_architecture.mermaid
    02_er_schema.mermaid
    03_rules_execution_flow.mermaid
    04_agent_interaction.mermaid
    05_agent_tools.mermaid
test_data/                   # SAP Material Master test data (MARA, MARC)
  01_ddl.sql
  02_seed_data.sql
api/                         # FastAPI backend
  Dockerfile
  requirements.txt
  main.py
  routers/                   # One router per resource group
    rules.py
    runs.py
    errors.py
    knowledge.py
    chat.py
  services/
    rules_executor.py        # Runs rule SQL against the data source
    agent.py                 # Claude agent with tool use
    embeddings.py            # pgvector embedding generation
  models/                    # SQLAlchemy ORM models
  db/
    session.py               # DB connection + session factory
    migrations/              # Alembic migrations
    init/
      01_app_schema.sql      # DQA application tables
      02_pgvector.sql        # Enable pgvector extension
      03_test_data.sql       # Load test data (dev only)
frontend/                    # React + TypeScript frontend
  Dockerfile
  package.json
  src/
    components/
      Dashboard/             # Rules list, error counts, trend charts
      Chat/                  # Agent chat interface
      Rules/                 # Rule detail, create/edit forms
      Knowledge/             # Knowledge base browser
    api/                     # Typed API client (fetch wrappers)
    types/                   # Shared TypeScript types
```

---

## Key Architectural Decisions

### Data Source Abstraction
The rules execution service connects to the *data source* (where ERP data lives) via a single environment variable. The application never hard-codes a connection type.

```
DATA_SOURCE_URL=postgresql://user:pass@postgres:5432/erp_data   # local dev
DATA_SOURCE_URL=redshift+psycopg2://...                          # production
```

The `rules_executor.py` service uses SQLAlchemy's engine factory with this URL directly. This is the single point of change when moving between environments. **Do not hard-code any connection strings anywhere else.**

### Two Separate Databases
There are two logical databases — keep them clearly separated in code:

- **App DB** (`APP_DB_URL`) — DQA application tables: rules, errors, summaries, knowledge base, conversations. Always PostgreSQL.
- **Data Source** (`DATA_SOURCE_URL`) — ERP data the rules run against. PostgreSQL locally, AWS Redshift in production.

In local dev both point to the same Postgres container but use different schemas/databases.

### Agent Tool Use
The agent is implemented using **LangGraph** with LangChain's model abstraction. This makes the agent model-agnostic — the underlying LLM can be swapped by changing `MODEL_PROVIDER` and `MODEL_NAME` environment variables without touching agent logic.

Key implementation pattern:
- Tools are defined with the `@tool` decorator from `langchain_core.tools`
- The model is instantiated via LangChain's provider integrations (e.g. `langchain_anthropic.ChatAnthropic`)
- The agent graph is built with `langgraph.prebuilt.create_react_agent` for the standard ReAct loop, or a custom `StateGraph` if more control is needed
- Conversation state (message history) is managed by LangGraph's `MessagesState`

```python
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic  # swap for langchain_openai, etc.

model = ChatAnthropic(model=settings.model_name)
agent = create_react_agent(model, tools=tool_list)
```

The model must be instantiated via a provider factory keyed on `MODEL_PROVIDER`. Implement this in a `services/model.py` module and import from there — never instantiate the model directly in agent.py:

```python
# services/model.py
from app.core.config import settings

def get_chat_model():
    if settings.model_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=settings.model_name)
    elif settings.model_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.model_name)
    else:
        raise ValueError(f"Unsupported MODEL_PROVIDER: {settings.model_provider}")

def get_embeddings_model():
    if settings.embeddings_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings()
    else:  # default: local via fastembed — no API key required
        from langchain_community.embeddings import FastEmbedEmbeddings
        return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
```

See `spec/diagrams/04_agent_interaction.mermaid` and `spec/diagrams/05_agent_tools.mermaid` for the full flow and tool inventory.

### Knowledge Base (pgvector)
Knowledge entries are stored in the `knowledge_entries` table with a `vector` column. Use LangChain's embeddings abstraction (`langchain_core.embeddings`) to generate embeddings — this keeps the embeddings model swappable via the `EMBEDDINGS_PROVIDER` env var. The default is `local`, which uses **fastembed** (`BAAI/bge-small-en-v1.5`) — a lightweight ONNX-based embeddings library that requires no API key and runs entirely inside the api container. `openai` is available as an alternative for higher-dimensional embeddings if needed. Use the `<=>` (cosine distance) operator for semantic search queries. Do not use a separate vector database — pgvector on the app DB is sufficient.

### No Scheduler in Dev
There is no scheduled job runner in local development. Rules are triggered manually via the API or by the agent. In production, Databricks job scheduler calls the `/runs` endpoint on a schedule.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `APP_DB_URL` | Yes | PostgreSQL connection for DQA app tables |
| `DATA_SOURCE_URL` | Yes | Connection for rule SQL execution (ERP data) |
| `MODEL_PROVIDER` | No | LLM provider — `anthropic` (default), `openai`, or `databricks` |
| `MODEL_NAME` | No | Model name — defaults to `claude-opus-4-6` |
| `EMBEDDINGS_PROVIDER` | No | Embeddings provider — `local` (default, uses fastembed), `openai`, or `databricks` |
| `ANTHROPIC_API_KEY` | No | Required when `MODEL_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | No | Required when `MODEL_PROVIDER=openai` or `EMBEDDINGS_PROVIDER=openai` |
| `DATABRICKS_HOST` | No | Databricks workspace URL (e.g. `https://adb-xxxx.azuredatabricks.net`) |
| `DATABRICKS_TOKEN` | No | Databricks PAT or OAuth token — required when provider is `databricks` |
| `ENV` | No | `development` or `production` — controls test data loading |

---

## Rule Schema

The `rules` table is the core of the system. Every rule must have:

- `sql_query` — a SELECT statement that returns rows only when a data problem exists. Zero rows = no error. Any rows = errors.
- `category` — one of: `completeness`, `validity`, `consistency`, `uniqueness`, `referential_integrity`, `timeliness`, `orphans`, `business_rules`
- `severity` — integer: `1`=info, `2`=warning, `3`=error, `4`=critical
- `is_active` — only active rules run in a batch execution

The `error_data` column in `rule_errors` stores the raw row returned by the rule SQL as JSONB. Rules should SELECT enough columns to make the error record meaningful (e.g., include `matnr`, `werks`, and the offending field value).

---

## Test Data

SAP Material Master test data (MARA + MARC tables) is in `test_data/`. Run in order:

```bash
psql $DATA_SOURCE_URL -f test_data/01_ddl.sql
psql $DATA_SOURCE_URL -f test_data/02_seed_data.sql
```

The seed data contains intentional data quality issues, each annotated with a `[DQ-ISSUE: CATEGORY]` comment. These are the targets for the initial rule set. When writing seed rules for the `rules` table, write at least one rule per category that catches one of these known issues.

---

## Running Locally

```bash
cp .env.example .env       # fill in ANTHROPIC_API_KEY
docker-compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Postgres: localhost:5432

---

## Code Conventions

- **Python**: use async/await throughout FastAPI routes and services. Use SQLAlchemy 2.0 async sessions.
- **TypeScript**: strict mode on. No `any` types. Define all API response shapes in `src/types/`.
- **SQL rules**: always alias the primary key column in rule SELECT statements so error records are identifiable.
- **Error handling**: API errors return `{"detail": "..."}` with appropriate HTTP status codes. Agent tool errors return a structured error result rather than raising — let the agent decide how to handle them.
- **Migrations**: use Alembic for all schema changes to the app DB. Never modify `init/` SQL files after initial setup.
