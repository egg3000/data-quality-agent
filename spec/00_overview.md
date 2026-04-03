# Data Quality Agent — System Specification

## Overview

The Data Quality Agent is a rules-based system for detecting and tracking data quality issues in ERP master data. At its core is a library of SQL rules — each rule is a query that, when it returns any records, signals a data error. An AI agent serves as the primary interface, enabling analysts to examine rules, write new ones, investigate errors, and build a persistent knowledge base of business domain expertise over time.

---

## Goals

- Detect data quality issues in ERP master data through configurable SQL rules
- Track errors over time and surface trends via a dashboard
- Build a growing repository of tribal business knowledge derived from rules and analyst conversations
- Provide a natural-language chat interface so analysts can interact with the system without writing SQL
- Support local development (all-in-one Docker Compose) and production deployment (Databricks Apps)

---

## Architecture

The system is composed of three Docker containers.

| Container | Technology | Responsibility |
|---|---|---|
| `postgres` | PostgreSQL 15 + pgvector | Application data, ERP mirror (dev), knowledge base embeddings |
| `api` | FastAPI (Python) | Rules execution service, AI agent, REST API |
| `frontend` | React.js | Dashboard, chat interface |

**Data source abstraction:** The rules execution service connects to the data source via a `DATA_SOURCE_URL` environment variable. In local development this points to the Postgres container (which holds mirrored ERP data). In production it will point to AWS Redshift. The application code has no awareness of which backend is in use.

See: [01_c4_architecture.mermaid](diagrams/01_c4_architecture.mermaid)

---

## Database Schema

All application state is stored in PostgreSQL. The key tables are:

- **rules** — the rule library (name, description, SQL query, severity, category)
- **rule_runs** — a log of every rule execution (triggered by scheduler, user, or agent)
- **rule_errors** — individual error records returned by each rule (raw row data as JSONB)
- **error_summaries** — daily aggregated counts per rule (used for trend charts)
- **knowledge_entries** — the knowledge base (human-readable entries + pgvector embeddings for semantic search)
- **conversations / conversation_messages** — full history of analyst chat sessions

See: [02_er_schema.mermaid](diagrams/02_er_schema.mermaid)

---

## Rule Severity

Severity is stored as an integer on each rule. This makes it easy to filter, sort, and compare programmatically without string matching. The current scale is:

| Level | Label | Meaning |
|---|---|---|
| 1 | Info | Informational — worth knowing, no immediate action required |
| 2 | Warning | Something is off and should be reviewed |
| 3 | Error | Definite data problem requiring correction |
| 4 | Critical | Reserved for future use — high-impact issues requiring urgent action |

The numeric approach keeps the schema simple and allows new levels to be inserted or the scale to be extended without a migration.

---

## Rule Categories

Each rule belongs to exactly one category. Categories reflect the nature of the data quality problem being detected, not the business domain. This distinction is important — a rule about vendor payment terms could be in any of these categories depending on what it's checking.

| Category | Description | Example |
|---|---|---|
| `completeness` | A required field is missing or empty | Active vendor has no payment terms code |
| `validity` | A field is populated but contains an invalid value | Tax ID doesn't match expected format |
| `consistency` | Two related fields or records contradict each other | Customer's sales org doesn't match their company code region |
| `uniqueness` | Duplicate or near-duplicate records exist | Two vendors share the same tax ID |
| `referential_integrity` | A record references something that doesn't exist or is inactive | Material assigned to an inactive plant |
| `timeliness` | A record is stale, expired, or overdue for review | Vendor master last reviewed more than 24 months ago |
| `orphans` | A record exists with no associated transactions or activity | Customer account with no orders in 36 months |
| `business_rules` | A company-specific policy is violated | Tier 2+ vendor missing diversity classification flag |

The `business_rules` category is intentionally broad — it captures rules that encode institutional knowledge rather than generic data quality principles. These are typically the most valuable rules and the hardest to write without domain expertise, making them a primary target for the agent's knowledge-capture capability.

---

## Rules Execution Service

Rules can be triggered three ways: on a schedule, manually by a user via the dashboard, or by the AI agent. When a run is triggered:

1. All active rules are loaded from the database
2. Each rule's SQL is executed against the configured data source
3. Any returned rows are saved as error records
4. The AI agent performs a post-run analysis, upserts daily summary records, and optionally writes a knowledge entry if a notable pattern is detected

See: [03_rules_execution_flow.mermaid](diagrams/03_rules_execution_flow.mermaid)

---

## AI Agent

The agent is built on **LangGraph** using LangChain's model abstraction layer. This means the underlying LLM is swappable via configuration — the system defaults to Claude (Anthropic) but can be pointed at OpenAI or other providers without changing agent logic. The agent serves four main purposes:

1. **Rule management** — examine existing rules, write new rules, explain what a rule checks for
2. **Error investigation** — query error summaries, drill into individual errors, spot patterns
3. **Knowledge capture** — save business knowledge derived from conversations and rule analysis
4. **Ongoing learning** — over time, the knowledge base grows into a repository of domain expertise that informs future agent responses

Tools are defined with LangChain's `@tool` decorator. The agent loop is managed by LangGraph's `create_react_agent`, with conversation state handled via `MessagesState`. The agent persists all conversations and, when it learns something non-obvious about the business domain, writes a structured knowledge entry with a pgvector embedding. Future conversations retrieve relevant knowledge via semantic search.

See: [04_agent_interaction.mermaid](diagrams/04_agent_interaction.mermaid)
See: [05_agent_tools.mermaid](diagrams/05_agent_tools.mermaid)

---

## Agent Tools Reference

| Tool | Purpose |
|---|---|
| `list_rules` | List all rules with metadata and active status |
| `get_rule` | Get full SQL and details for a specific rule |
| `create_rule` | Write a new rule — name, SQL, category, severity |
| `update_rule` | Modify an existing rule's SQL or metadata |
| `run_rule` | Execute a specific rule immediately |
| `run_all_rules` | Trigger a full rule execution batch |
| `get_error_summary` | Error counts and trends for a rule or date range |
| `get_errors` | Individual error records from a rule run |
| `get_run_history` | List past rule runs with status and counts |
| `search_knowledge` | Semantic search of knowledge entries (pgvector) |
| `write_knowledge` | Save a new knowledge entry with auto-generated embedding |
| `list_knowledge` | List knowledge entries by tag or source type |
| `get_conversation_history` | Retrieve prior messages for the current session |
| `search_conversations` | Semantic search across past analyst conversations |

---

## Deployment

### Local Development (Docker Compose)

All three containers run locally via `docker-compose up`. The `DATA_SOURCE_URL` env var points to the local Postgres container. For development and testing, the Postgres container is seeded with synthetic test data that mimics ERP master data structures — no live ERP connection is required at this stage.

### Production (Databricks Apps)

The `api` and `frontend` containers are deployed as Databricks Apps. The `DATA_SOURCE_URL` env var is updated to point to the AWS Redshift instance. The Postgres container remains as the application database (rules, errors, knowledge base).

---

## Open Questions

- What ERP system(s) will be the data source in production? This affects the SQL dialect and the Redshift replication strategy.
- Which additional SAP master data domains should get test data? (Customer — KNA1/KNVV, Vendor — LFA1/LFB1, GL Accounts — SKA1/SKB1, etc.)

## Decisions Log

| Decision | Detail |
|---|---|
| ERP replication | Out of scope. Data is assumed to already be in AWS Redshift (prod) or Postgres (dev). No ETL pipeline required. |
| Knowledge entry saving | Auto-saved by the agent. A review/feedback mechanism for power users will be added as a later feature. |
| Scheduler in dev | Not implemented in local dev. In production, Databricks job scheduler handles rule execution scheduling. |
| Test data | SAP Material Master (MARA + MARC tables) as the initial test data domain. See `test_data/` folder. |
| Agent framework | LangGraph + LangChain model abstraction. Model-agnostic by design — defaults to Claude (Anthropic) but swappable via `MODEL_PROVIDER` / `MODEL_NAME` env vars. |
| Embeddings | fastembed (`BAAI/bge-small-en-v1.5`) as the default local provider — ONNX-based, no API key needed, runs inside the api container. OpenAI embeddings available as an alternative via `EMBEDDINGS_PROVIDER=openai`. |
