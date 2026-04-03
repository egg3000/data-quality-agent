-- ============================================================
-- pgvector HNSW index for semantic search on knowledge entries
-- Runs after 01_app_schema.sql creates the table and vector column
-- ============================================================

CREATE INDEX idx_knowledge_embedding ON knowledge_entries
    USING hnsw (embedding vector_cosine_ops);
