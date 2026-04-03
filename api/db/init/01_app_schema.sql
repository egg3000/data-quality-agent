-- ============================================================
-- Data Quality Agent — Application Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------------------------------------
-- Rules: the core rule library
-- -------------------------------------------------------
CREATE TABLE rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    category    VARCHAR(30) NOT NULL CHECK (category IN (
                    'completeness', 'validity', 'consistency', 'uniqueness',
                    'referential_integrity', 'timeliness', 'orphans', 'business_rules'
                )),
    severity    INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 4),
    sql_query   TEXT NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_by  VARCHAR(100),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -------------------------------------------------------
-- Rule Runs: execution log
-- -------------------------------------------------------
CREATE TABLE rule_runs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id       UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    triggered_by  VARCHAR(20) NOT NULL CHECK (triggered_by IN ('scheduler', 'user', 'agent')),
    status        VARCHAR(20) NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    error_count   INTEGER DEFAULT 0,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX idx_rule_runs_rule_id ON rule_runs(rule_id);
CREATE INDEX idx_rule_runs_started_at ON rule_runs(started_at DESC);

-- -------------------------------------------------------
-- Rule Errors: individual error records
-- -------------------------------------------------------
CREATE TABLE rule_errors (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id     UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    rule_run_id UUID NOT NULL REFERENCES rule_runs(id) ON DELETE CASCADE,
    error_data  JSONB NOT NULL,
    is_resolved BOOLEAN NOT NULL DEFAULT false,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_rule_errors_rule_id ON rule_errors(rule_id);
CREATE INDEX idx_rule_errors_rule_run_id ON rule_errors(rule_run_id);

-- -------------------------------------------------------
-- Error Summaries: daily aggregated counts per rule
-- -------------------------------------------------------
CREATE TABLE error_summaries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id         UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    summary_date    DATE NOT NULL,
    total_errors    INTEGER NOT NULL DEFAULT 0,
    new_errors      INTEGER NOT NULL DEFAULT 0,
    resolved_errors INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB,
    UNIQUE (rule_id, summary_date)
);

CREATE INDEX idx_error_summaries_rule_date ON error_summaries(rule_id, summary_date);

-- -------------------------------------------------------
-- Knowledge Entries: business knowledge with embeddings
-- -------------------------------------------------------
CREATE TABLE knowledge_entries (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(300) NOT NULL,
    content     TEXT NOT NULL,
    source_type VARCHAR(30) NOT NULL CHECK (source_type IN ('agent', 'analyst', 'rule', 'conversation')),
    source_id   UUID,
    embedding   vector(384),
    tags        TEXT[],
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -------------------------------------------------------
-- Conversations: chat session tracking
-- -------------------------------------------------------
CREATE TABLE conversations (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id     VARCHAR(200) NOT NULL UNIQUE,
    analyst_id     VARCHAR(100),
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -------------------------------------------------------
-- Conversation Messages: full chat history
-- -------------------------------------------------------
CREATE TABLE conversation_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content         TEXT,
    tool_calls      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversation_messages_conv_id ON conversation_messages(conversation_id);
