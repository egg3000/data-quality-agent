import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_app_db
from models.error_summary import ErrorSummary
from models.rule import Rule
from models.rule_error import RuleError
from schemas.errors import ErrorResolveRequest, ErrorResponse, ErrorSummaryItem

router = APIRouter(prefix="/errors", tags=["errors"])


@router.get("/summary", response_model=list[ErrorSummaryItem])
async def get_error_summary(
    rule_id: Optional[uuid.UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_app_db),
):
    stmt = select(ErrorSummary)
    if rule_id is not None:
        stmt = stmt.where(ErrorSummary.rule_id == rule_id)
    if start_date is not None:
        stmt = stmt.where(ErrorSummary.summary_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(ErrorSummary.summary_date <= end_date)
    stmt = stmt.order_by(ErrorSummary.summary_date.desc())
    result = await db.execute(stmt)
    summaries = result.scalars().all()

    items = []
    for s in summaries:
        rule_result = await db.execute(select(Rule.name).where(Rule.id == s.rule_id))
        rule_name = rule_result.scalar_one_or_none()
        items.append(ErrorSummaryItem(
            rule_id=s.rule_id,
            rule_name=rule_name,
            summary_date=s.summary_date,
            total_errors=s.total_errors,
            new_errors=s.new_errors,
            resolved_errors=s.resolved_errors,
        ))
    return items


@router.get("/", response_model=list[ErrorResponse])
async def list_errors(
    rule_id: Optional[uuid.UUID] = Query(None),
    run_id: Optional[uuid.UUID] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_app_db),
):
    stmt = select(RuleError)
    if rule_id is not None:
        stmt = stmt.where(RuleError.rule_id == rule_id)
    if run_id is not None:
        stmt = stmt.where(RuleError.rule_run_id == run_id)
    if is_resolved is not None:
        stmt = stmt.where(RuleError.is_resolved == is_resolved)
    stmt = stmt.order_by(RuleError.detected_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    errors = result.scalars().all()

    responses = []
    for err in errors:
        rule_result = await db.execute(select(Rule.name).where(Rule.id == err.rule_id))
        rule_name = rule_result.scalar_one_or_none()
        responses.append(ErrorResponse(
            id=err.id,
            rule_id=err.rule_id,
            rule_run_id=err.rule_run_id,
            rule_name=rule_name,
            error_data=err.error_data,
            is_resolved=err.is_resolved,
            detected_at=err.detected_at,
            resolved_at=err.resolved_at,
        ))
    return responses


@router.get("/{error_id}", response_model=ErrorResponse)
async def get_error(error_id: uuid.UUID, db: AsyncSession = Depends(get_app_db)):
    result = await db.execute(select(RuleError).where(RuleError.id == error_id))
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    rule_result = await db.execute(select(Rule.name).where(Rule.id == error.rule_id))
    rule_name = rule_result.scalar_one_or_none()
    return ErrorResponse(
        id=error.id,
        rule_id=error.rule_id,
        rule_run_id=error.rule_run_id,
        rule_name=rule_name,
        error_data=error.error_data,
        is_resolved=error.is_resolved,
        detected_at=error.detected_at,
        resolved_at=error.resolved_at,
    )


@router.patch("/{error_id}", response_model=ErrorResponse)
async def resolve_error(
    error_id: uuid.UUID,
    body: ErrorResolveRequest,
    db: AsyncSession = Depends(get_app_db),
):
    from datetime import datetime, timezone

    result = await db.execute(select(RuleError).where(RuleError.id == error_id))
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    error.is_resolved = body.is_resolved
    error.resolved_at = datetime.now(timezone.utc) if body.is_resolved else None
    await db.commit()
    await db.refresh(error)

    rule_result = await db.execute(select(Rule.name).where(Rule.id == error.rule_id))
    rule_name = rule_result.scalar_one_or_none()
    return ErrorResponse(
        id=error.id,
        rule_id=error.rule_id,
        rule_run_id=error.rule_run_id,
        rule_name=rule_name,
        error_data=error.error_data,
        is_resolved=error.is_resolved,
        detected_at=error.detected_at,
        resolved_at=error.resolved_at,
    )
