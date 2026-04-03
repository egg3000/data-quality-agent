import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_app_db
from models.knowledge import KnowledgeEntry
from schemas.knowledge import (
    VALID_SOURCE_TYPES,
    KnowledgeCreate,
    KnowledgeResponse,
    KnowledgeSearchResult,
)
from services.embeddings import generate_embedding, search_by_similarity

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=list[KnowledgeSearchResult])
async def search_knowledge(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_app_db),
):
    results = await search_by_similarity(q, limit=limit, session=db)
    return [
        KnowledgeSearchResult(
            entry=KnowledgeResponse.model_validate(entry),
            similarity=1.0 - distance,  # cosine distance → similarity
        )
        for entry, distance in results
    ]


@router.get("/", response_model=list[KnowledgeResponse])
async def list_knowledge(
    source_type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_app_db),
):
    stmt = select(KnowledgeEntry)
    if source_type is not None:
        stmt = stmt.where(KnowledgeEntry.source_type == source_type)
    if tag is not None:
        stmt = stmt.where(KnowledgeEntry.tags.any(tag))
    stmt = stmt.order_by(KnowledgeEntry.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{entry_id}", response_model=KnowledgeResponse)
async def get_knowledge_entry(
    entry_id: uuid.UUID, db: AsyncSession = Depends(get_app_db)
):
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.post("/", response_model=KnowledgeResponse, status_code=201)
async def create_knowledge_entry(
    body: KnowledgeCreate, db: AsyncSession = Depends(get_app_db)
):
    if body.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid source_type. Must be one of: {VALID_SOURCE_TYPES}",
        )

    embedding = await generate_embedding(f"{body.title} {body.content}")

    entry = KnowledgeEntry(
        title=body.title,
        content=body.content,
        source_type=body.source_type,
        source_id=body.source_id,
        tags=body.tags,
        embedding=embedding,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_knowledge_entry(
    entry_id: uuid.UUID, db: AsyncSession = Depends(get_app_db)
):
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    await db.delete(entry)
    await db.commit()
