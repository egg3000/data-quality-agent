import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_app_db
from models.rule import Rule
from schemas.rules import VALID_CATEGORIES, RuleCreate, RuleResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/", response_model=list[RuleResponse])
async def list_rules(
    category: Optional[str] = Query(None),
    severity: Optional[int] = Query(None, ge=1, le=4),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_app_db),
):
    stmt = select(Rule)
    if category is not None:
        stmt = stmt.where(Rule.category == category)
    if severity is not None:
        stmt = stmt.where(Rule.severity == severity)
    if is_active is not None:
        stmt = stmt.where(Rule.is_active == is_active)
    stmt = stmt.order_by(Rule.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_app_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("/", response_model=RuleResponse, status_code=201)
async def create_rule(body: RuleCreate, db: AsyncSession = Depends(get_app_db)):
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Invalid category. Must be one of: {VALID_CATEGORIES}")
    rule = Rule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: uuid.UUID, body: RuleUpdate, db: AsyncSession = Depends(get_app_db)
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    updates = body.model_dump(exclude_unset=True)
    if "category" in updates and updates["category"] not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Invalid category. Must be one of: {VALID_CATEGORIES}")

    for field, value in updates.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_app_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
