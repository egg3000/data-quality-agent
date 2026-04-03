import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.error_summary import ErrorSummary
from models.rule import Rule
from models.rule_error import RuleError
from models.rule_run import RuleRun

logger = logging.getLogger(__name__)


def _jsonable(v):
    """Convert a SQL row value to a JSON-serializable type."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


async def execute_rule(
    rule: Rule,
    triggered_by: str,
    app_session: AsyncSession,
    data_source_session: AsyncSession,
) -> RuleRun:
    """Execute a single rule's SQL against the data source and store results."""
    run = RuleRun(
        rule_id=rule.id,
        triggered_by=triggered_by,
        status="running",
        error_count=0,
    )
    app_session.add(run)
    await app_session.flush()

    try:
        result = await data_source_session.execute(text(rule.sql_query))
        rows = result.mappings().all()

        for row in rows:
            error = RuleError(
                rule_id=rule.id,
                rule_run_id=run.id,
                error_data={k: _jsonable(v) for k, v in dict(row).items()},
            )
            app_session.add(error)

        run.status = "completed"
        run.error_count = len(rows)
        run.completed_at = datetime.now(timezone.utc)

    except Exception as e:
        logger.error(f"Rule '{rule.name}' (id={rule.id}) failed: {e}")
        run.status = "failed"
        run.error_count = 0
        run.completed_at = datetime.now(timezone.utc)

    await app_session.flush()
    return run


async def _upsert_error_summaries(
    runs: list[RuleRun],
    app_session: AsyncSession,
) -> None:
    """Upsert daily error summary records for each rule that ran."""
    today = date.today()

    for run in runs:
        if run.status != "completed":
            continue

        result = await app_session.execute(
            select(ErrorSummary).where(
                ErrorSummary.rule_id == run.rule_id,
                ErrorSummary.summary_date == today,
            )
        )
        summary = result.scalar_one_or_none()

        if summary:
            summary.total_errors = run.error_count
        else:
            summary = ErrorSummary(
                rule_id=run.rule_id,
                summary_date=today,
                total_errors=run.error_count,
                new_errors=run.error_count,
                resolved_errors=0,
            )
            app_session.add(summary)

    await app_session.flush()


async def _run_post_analysis(runs: list[RuleRun]) -> None:
    """Invoke the AI agent for post-run analysis if available."""
    try:
        from services.agent import get_agent
        from langchain_core.messages import HumanMessage, SystemMessage

        completed = [r for r in runs if r.status == "completed"]
        if not completed:
            return

        total_errors = sum(r.error_count for r in completed)
        rules_with_errors = [r for r in completed if r.error_count > 0]

        summary_text = (
            f"Rule execution batch complete. "
            f"{len(completed)} rules ran, {total_errors} total errors found across "
            f"{len(rules_with_errors)} rules. "
            f"Please review the results using your tools. "
            f"If you notice any notable patterns or anomalies, write a knowledge entry."
        )

        agent = get_agent()
        await agent.ainvoke({
            "messages": [
                SystemMessage(content="You are performing post-run analysis of data quality rules. Use your tools to review results and capture any notable insights as knowledge entries."),
                HumanMessage(content=summary_text),
            ]
        })
    except Exception as e:
        logger.warning(f"Post-run analysis skipped: {e}")


async def execute_all_rules(
    triggered_by: str,
    app_session: AsyncSession,
    data_source_session: AsyncSession,
    run_post_analysis: bool = False,
) -> list[RuleRun]:
    """Execute all active rules and return the list of run records."""
    result = await app_session.execute(
        select(Rule).where(Rule.is_active == True)
    )
    rules = result.scalars().all()

    runs = []
    for rule in rules:
        run = await execute_rule(rule, triggered_by, app_session, data_source_session)
        runs.append(run)

    await _upsert_error_summaries(runs, app_session)
    await app_session.commit()

    if run_post_analysis:
        await _run_post_analysis(runs)

    return runs
