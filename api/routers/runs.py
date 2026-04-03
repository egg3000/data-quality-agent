import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_app_db, get_data_source
from models.rule import Rule
from models.rule_run import RuleRun
from schemas.runs import RunBatchResponse, RunResponse, RunTrigger
from services.rules_executor import execute_all_rules, execute_rule

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("/", response_model=RunBatchResponse)
async def trigger_run(
    body: RunTrigger = RunTrigger(),
    app_db: AsyncSession = Depends(get_app_db),
    data_source: AsyncSession = Depends(get_data_source),
):
    if body.rule_id:
        result = await app_db.execute(select(Rule).where(Rule.id == body.rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        run = await execute_rule(rule, "user", app_db, data_source)
        await app_db.commit()
        runs = [run]
    else:
        runs = await execute_all_rules("user", app_db, data_source)

    run_responses = []
    for run in runs:
        rule_result = await app_db.execute(select(Rule.name).where(Rule.id == run.rule_id))
        rule_name = rule_result.scalar_one_or_none()
        run_responses.append(RunResponse(
            id=run.id,
            rule_id=run.rule_id,
            rule_name=rule_name,
            triggered_by=run.triggered_by,
            status=run.status,
            error_count=run.error_count,
            started_at=run.started_at,
            completed_at=run.completed_at,
        ))

    return RunBatchResponse(
        total_rules=len(runs),
        completed=sum(1 for r in runs if r.status == "completed"),
        failed=sum(1 for r in runs if r.status == "failed"),
        total_errors=sum(r.error_count for r in runs),
        runs=run_responses,
    )


@router.get("/", response_model=list[RunResponse])
async def list_runs(
    rule_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_app_db),
):
    stmt = select(RuleRun)
    if rule_id is not None:
        stmt = stmt.where(RuleRun.rule_id == rule_id)
    if status is not None:
        stmt = stmt.where(RuleRun.status == status)
    stmt = stmt.order_by(RuleRun.started_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    runs = result.scalars().all()

    responses = []
    for run in runs:
        rule_result = await db.execute(select(Rule.name).where(Rule.id == run.rule_id))
        rule_name = rule_result.scalar_one_or_none()
        responses.append(RunResponse(
            id=run.id,
            rule_id=run.rule_id,
            rule_name=rule_name,
            triggered_by=run.triggered_by,
            status=run.status,
            error_count=run.error_count,
            started_at=run.started_at,
            completed_at=run.completed_at,
        ))
    return responses


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_app_db)):
    result = await db.execute(select(RuleRun).where(RuleRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    rule_result = await db.execute(select(Rule.name).where(Rule.id == run.rule_id))
    rule_name = rule_result.scalar_one_or_none()
    return RunResponse(
        id=run.id,
        rule_id=run.rule_id,
        rule_name=rule_name,
        triggered_by=run.triggered_by,
        status=run.status,
        error_count=run.error_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )
