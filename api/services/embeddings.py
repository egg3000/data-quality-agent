from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import KnowledgeEntry
from services.model import get_embeddings_model

_embeddings_model = None


def _get_model():
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = get_embeddings_model()
    return _embeddings_model


async def generate_embedding(content: str) -> list[float]:
    """Generate a vector embedding for the given text."""
    model = _get_model()
    return model.embed_query(content)


async def search_by_similarity(
    query: str,
    limit: int = 5,
    session: AsyncSession = None,
) -> list[tuple[KnowledgeEntry, float]]:
    """Semantic search over knowledge entries using pgvector cosine distance.

    Returns list of (entry, distance) tuples, sorted by relevance (lowest distance first).
    """
    query_embedding = await generate_embedding(query)

    # Use raw SQL for pgvector cosine distance operator
    # Format embedding as pgvector literal: '[0.1,0.2,...]'
    embedding_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"

    stmt = text("""
        SELECT id, title, content, source_type, source_id, tags, created_at, updated_at,
               embedding <=> cast(:query_embedding as vector) AS distance
        FROM knowledge_entries
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> cast(:query_embedding as vector)
        LIMIT :limit
    """)

    result = await session.execute(stmt, {
        "query_embedding": embedding_literal,
        "limit": limit,
    })
    rows = result.mappings().all()

    entries = []
    for row in rows:
        entry = KnowledgeEntry(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            tags=row["tags"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        entries.append((entry, row["distance"]))

    return entries
