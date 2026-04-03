import uuid
from datetime import datetime, timezone
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import AppSessionLocal, DataSourceSessionLocal
from models.conversation import Conversation, ConversationMessage
from models.error_summary import ErrorSummary
from models.knowledge import KnowledgeEntry
from models.rule import Rule
from models.rule_error import RuleError
from models.rule_run import RuleRun
from services.embeddings import generate_embedding, search_by_similarity
from services.model import get_chat_model
from services.rules_executor import execute_all_rules, execute_rule

SYSTEM_PROMPT = """You are a Data Quality Agent that helps analysts investigate and manage data quality rules for ERP master data.

You have access to tools for:
- **Rule Management**: List, view, create, update, and execute data quality rules
- **Error Investigation**: View error summaries, individual errors, and run history
- **Data Exploration**: List tables and run read-only SQL queries against the ERP data source (MARA, MARC, T001W, T134, T023)
- **Knowledge Base**: Search, create, and browse business knowledge entries
- **Conversation History**: Retrieve past conversations

Key behaviors:
- When asked about data quality issues, use your tools to look up actual data rather than guessing
- When you learn something non-obvious about the business domain during a conversation, proactively write a knowledge entry to capture that insight
- Before answering domain-specific questions, search the knowledge base for relevant prior knowledge
- When presenting errors, include the material number (matnr) and plant (werks) so analysts can take action
- Be specific and data-driven in your responses — cite actual counts, rule names, and error details
- **Always format tabular data as proper markdown tables** with header rows, separator rows, and aligned columns. Never output raw Python dicts or unstructured lists when a table would be clearer.

Rule categories: completeness, validity, consistency, uniqueness, referential_integrity, timeliness, orphans, business_rules
Severity levels: 1=info, 2=warning, 3=error, 4=critical
"""


# --- Tool definitions ---
# Tools use standalone async sessions so they work inside the LangGraph loop.

@tool
async def list_rules(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> str:
    """List all data quality rules with their metadata and active status.
    Optionally filter by category or active status."""
    async with AppSessionLocal() as session:
        stmt = select(Rule)
        if category:
            stmt = stmt.where(Rule.category == category)
        if is_active is not None:
            stmt = stmt.where(Rule.is_active == is_active)
        stmt = stmt.order_by(Rule.name)
        result = await session.execute(stmt)
        rules = result.scalars().all()

        if not rules:
            return "No rules found matching the criteria."

        header = "| Status | Name | Category | Severity | ID |"
        separator = "| --- | --- | --- | --- | --- |"
        rows = []
        for r in rules:
            status = "Active" if r.is_active else "Inactive"
            rows.append(f"| {status} | {r.name} | {r.category} | {r.severity} | {r.id} |")
        return f"Found {len(rules)} rules:\n\n{header}\n{separator}\n" + "\n".join(rows)


@tool
async def get_rule(rule_id: str) -> str:
    """Get the full SQL query and details for a specific rule by its UUID."""
    async with AppSessionLocal() as session:
        result = await session.execute(select(Rule).where(Rule.id == uuid.UUID(rule_id)))
        rule = result.scalar_one_or_none()
        if not rule:
            return f"Rule {rule_id} not found."
        return (
            f"Rule: {rule.name}\n"
            f"ID: {rule.id}\n"
            f"Category: {rule.category}\n"
            f"Severity: {rule.severity}\n"
            f"Active: {rule.is_active}\n"
            f"Description: {rule.description}\n"
            f"SQL:\n{rule.sql_query}\n"
            f"Created by: {rule.created_by} on {rule.created_at}"
        )


@tool
async def create_rule(
    name: str,
    sql_query: str,
    category: str,
    severity: int,
    description: Optional[str] = None,
) -> str:
    """Create a new data quality rule. The SQL should return rows only when a data problem exists."""
    async with AppSessionLocal() as session:
        rule = Rule(
            name=name,
            description=description,
            category=category,
            severity=severity,
            sql_query=sql_query,
            is_active=True,
            created_by="agent",
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        return f"Created rule '{rule.name}' with id={rule.id}"


@tool
async def update_rule(
    rule_id: str,
    name: Optional[str] = None,
    sql_query: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[int] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> str:
    """Update an existing rule's SQL, metadata, or active status."""
    async with AppSessionLocal() as session:
        result = await session.execute(select(Rule).where(Rule.id == uuid.UUID(rule_id)))
        rule = result.scalar_one_or_none()
        if not rule:
            return f"Rule {rule_id} not found."

        if name is not None:
            rule.name = name
        if sql_query is not None:
            rule.sql_query = sql_query
        if category is not None:
            rule.category = category
        if severity is not None:
            rule.severity = severity
        if description is not None:
            rule.description = description
        if is_active is not None:
            rule.is_active = is_active

        await session.commit()
        return f"Updated rule '{rule.name}' (id={rule.id})"


@tool
async def run_rule(rule_id: str) -> str:
    """Execute a specific rule immediately against the data source and return results."""
    async with AppSessionLocal() as app_session:
        result = await app_session.execute(select(Rule).where(Rule.id == uuid.UUID(rule_id)))
        rule = result.scalar_one_or_none()
        if not rule:
            return f"Rule {rule_id} not found."

        async with DataSourceSessionLocal() as ds_session:
            run = await execute_rule(rule, "agent", app_session, ds_session)
            await app_session.commit()

        status_msg = f"completed with {run.error_count} error(s)" if run.status == "completed" else f"failed"
        return f"Rule '{rule.name}' {status_msg}. Run ID: {run.id}"


@tool
async def run_all_rules() -> str:
    """Trigger a full execution batch of all active rules and return a summary."""
    async with AppSessionLocal() as app_session:
        async with DataSourceSessionLocal() as ds_session:
            runs = await execute_all_rules("agent", app_session, ds_session)

    completed = [r for r in runs if r.status == "completed"]
    failed = [r for r in runs if r.status == "failed"]
    total_errors = sum(r.error_count for r in runs)

    lines = [f"Executed {len(runs)} rules: {len(completed)} completed, {len(failed)} failed, {total_errors} total errors."]
    for r in runs:
        lines.append(f"  - Rule {r.rule_id}: {r.status}, {r.error_count} errors")
    return "\n".join(lines)


@tool
async def get_error_summary(
    rule_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Get error counts and trends for a rule or date range. Dates in YYYY-MM-DD format."""
    async with AppSessionLocal() as session:
        stmt = select(ErrorSummary)
        if rule_id:
            stmt = stmt.where(ErrorSummary.rule_id == uuid.UUID(rule_id))
        if start_date:
            stmt = stmt.where(ErrorSummary.summary_date >= start_date)
        if end_date:
            stmt = stmt.where(ErrorSummary.summary_date <= end_date)
        stmt = stmt.order_by(ErrorSummary.summary_date.desc()).limit(50)
        result = await session.execute(stmt)
        summaries = result.scalars().all()

        if not summaries:
            return "No error summaries found. Summaries are generated after rule execution."

        header = "| Date | Rule ID | Total | New | Resolved |"
        separator = "| --- | --- | --- | --- | --- |"
        rows = []
        for s in summaries:
            rows.append(f"| {s.summary_date} | {s.rule_id} | {s.total_errors} | {s.new_errors} | {s.resolved_errors} |")
        return f"Found {len(summaries)} summary records:\n\n{header}\n{separator}\n" + "\n".join(rows)


@tool
async def get_errors(
    rule_id: Optional[str] = None,
    run_id: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Get individual error records from rule runs. Returns the error data as JSON."""
    async with AppSessionLocal() as session:
        stmt = select(RuleError)
        if rule_id:
            stmt = stmt.where(RuleError.rule_id == uuid.UUID(rule_id))
        if run_id:
            stmt = stmt.where(RuleError.rule_run_id == uuid.UUID(run_id))
        stmt = stmt.order_by(RuleError.detected_at.desc()).limit(limit)
        result = await session.execute(stmt)
        errors = result.scalars().all()

        if not errors:
            return "No errors found matching the criteria."

        # Build a markdown table from error_data dicts
        all_keys: list[str] = []
        for e in errors:
            for k in e.error_data:
                if k not in all_keys:
                    all_keys.append(k)

        header_cols = ["status"] + all_keys
        header = "| " + " | ".join(header_cols) + " |"
        separator = "| " + " | ".join("---" for _ in header_cols) + " |"
        rows = []
        for e in errors:
            status = "RESOLVED" if e.is_resolved else "OPEN"
            row_vals = [status] + [str(e.error_data.get(k, "")) for k in all_keys]
            rows.append("| " + " | ".join(row_vals) + " |")

        return f"Found {len(errors)} errors:\n\n{header}\n{separator}\n" + "\n".join(rows)


@tool
async def get_run_history(
    rule_id: Optional[str] = None,
    limit: int = 10,
) -> str:
    """List past rule runs with status and error counts."""
    async with AppSessionLocal() as session:
        stmt = select(RuleRun)
        if rule_id:
            stmt = stmt.where(RuleRun.rule_id == uuid.UUID(rule_id))
        stmt = stmt.order_by(RuleRun.started_at.desc()).limit(limit)
        result = await session.execute(stmt)
        runs = result.scalars().all()

        if not runs:
            return "No run history found."

        lines = []
        for r in runs:
            lines.append(
                f"  Run {r.id}: rule={r.rule_id}, status={r.status}, "
                f"errors={r.error_count}, triggered_by={r.triggered_by}, "
                f"started={r.started_at}"
            )
        return f"Found {len(runs)} runs:\n" + "\n".join(lines)


@tool
async def search_knowledge(query: str, limit: int = 5) -> str:
    """Semantic search of knowledge entries using vector similarity."""
    async with AppSessionLocal() as session:
        results = await search_by_similarity(query, limit=limit, session=session)

        if not results:
            return "No knowledge entries found matching your query."

        lines = []
        for entry, distance in results:
            similarity = 1.0 - distance
            lines.append(
                f"  [{similarity:.2f}] {entry.title} (id={entry.id})\n"
                f"    {entry.content[:200]}..."
                if len(entry.content) > 200
                else f"  [{similarity:.2f}] {entry.title} (id={entry.id})\n    {entry.content}"
            )
        return f"Found {len(results)} relevant entries:\n" + "\n".join(lines)


@tool
async def write_knowledge(
    title: str,
    content: str,
    source_type: str = "agent",
    tags: Optional[list[str]] = None,
) -> str:
    """Save a new knowledge entry with auto-generated embedding for future semantic search."""
    async with AppSessionLocal() as session:
        embedding = await generate_embedding(f"{title} {content}")
        entry = KnowledgeEntry(
            title=title,
            content=content,
            source_type=source_type,
            tags=tags or [],
            embedding=embedding,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return f"Knowledge entry '{entry.title}' saved with id={entry.id}"


@tool
async def list_knowledge(
    source_type: Optional[str] = None,
    tag: Optional[str] = None,
) -> str:
    """List knowledge entries, optionally filtered by source type or tag."""
    async with AppSessionLocal() as session:
        stmt = select(KnowledgeEntry)
        if source_type:
            stmt = stmt.where(KnowledgeEntry.source_type == source_type)
        if tag:
            stmt = stmt.where(KnowledgeEntry.tags.any(tag))
        stmt = stmt.order_by(KnowledgeEntry.created_at.desc()).limit(20)
        result = await session.execute(stmt)
        entries = result.scalars().all()

        if not entries:
            return "No knowledge entries found."

        lines = []
        for e in entries:
            tags_str = ", ".join(e.tags) if e.tags else "none"
            lines.append(f"  - {e.title} (id={e.id}, source={e.source_type}, tags=[{tags_str}])")
        return f"Found {len(entries)} entries:\n" + "\n".join(lines)


@tool
async def get_conversation_history(conversation_id: str) -> str:
    """Retrieve prior messages for a conversation session."""
    async with AppSessionLocal() as session:
        result = await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == uuid.UUID(conversation_id))
            .order_by(ConversationMessage.created_at)
        )
        messages = result.scalars().all()

        if not messages:
            return "No messages found for this conversation."

        lines = []
        for m in messages:
            lines.append(f"  [{m.role}] {m.content[:200] if m.content else '(tool call)'}")
        return f"Conversation has {len(messages)} messages:\n" + "\n".join(lines)


@tool
async def search_conversations(query: str) -> str:
    """Search across past analyst conversations by keyword."""
    async with AppSessionLocal() as session:
        # Simple text search across conversation messages
        stmt = text("""
            SELECT cm.id, cm.conversation_id, cm.role, cm.content, cm.created_at
            FROM conversation_messages cm
            WHERE cm.content ILIKE :pattern
            ORDER BY cm.created_at DESC
            LIMIT 10
        """)
        result = await session.execute(stmt, {"pattern": f"%{query}%"})
        rows = result.mappings().all()

        if not rows:
            return "No conversations found matching your query."

        lines = []
        for r in rows:
            lines.append(
                f"  [{r['role']}] (conv={r['conversation_id']}, {r['created_at']}): "
                f"{r['content'][:150] if r['content'] else '(empty)'}"
            )
        return f"Found {len(rows)} matching messages:\n" + "\n".join(lines)


MAX_QUERY_ROWS = 50
BLOCKED_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "truncate", "create", "grant", "revoke"}


@tool
async def list_tables() -> str:
    """List all tables available in the ERP data source with their columns."""
    async with DataSourceSessionLocal() as session:
        result = await session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = [r[0] for r in result.all()]

        if not tables:
            return "No tables found in the data source."

        lines = []
        for table in tables:
            col_result = await session.execute(text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :table "
                "ORDER BY ordinal_position"
            ), {"table": table})
            cols = col_result.all()
            col_list = ", ".join(f"{c[0]} ({c[1]})" for c in cols)
            lines.append(f"**{table}**: {col_list}")

        return "Tables in data source:\n\n" + "\n\n".join(lines)


@tool
async def query_data(sql: str, limit: int = 20) -> str:
    """Run a read-only SQL query against the ERP data source and return results as a markdown table.

    Safeguards:
    - Only SELECT statements are allowed (no INSERT, UPDATE, DELETE, DDL).
    - Results are capped at 50 rows maximum. Use the limit parameter to control (default 20).
    - For large tables, always include a WHERE clause or LIMIT to avoid scanning everything.
    """
    # Validate: only SELECT allowed
    stripped = sql.strip().rstrip(";").strip()
    first_word = stripped.split()[0].lower() if stripped else ""
    if first_word != "select":
        return "Error: Only SELECT queries are allowed. Cannot run INSERT, UPDATE, DELETE, or DDL statements."

    # Check for dangerous keywords anywhere in the query
    lower_sql = stripped.lower()
    for kw in BLOCKED_KEYWORDS:
        # Check as whole word to avoid false positives (e.g. "deleted" matching "delete")
        if f" {kw} " in f" {lower_sql} " or lower_sql.startswith(f"{kw} "):
            return f"Error: Query contains blocked keyword '{kw}'. Only SELECT queries are allowed."

    # Enforce row limit
    effective_limit = min(limit, MAX_QUERY_ROWS)

    # Wrap in a subquery to enforce the limit reliably
    safe_sql = f"SELECT * FROM ({stripped}) AS _q LIMIT {effective_limit}"

    async with DataSourceSessionLocal() as session:
        try:
            result = await session.execute(text(safe_sql))
            rows = result.mappings().all()
        except Exception as e:
            return f"Query error: {e}"

        if not rows:
            return "Query returned 0 rows."

        # Build markdown table
        keys = list(rows[0].keys())
        header = "| " + " | ".join(keys) + " |"
        separator = "| " + " | ".join("---" for _ in keys) + " |"
        data_rows = []
        for row in rows:
            vals = [str(row[k]) if row[k] is not None else "" for k in keys]
            data_rows.append("| " + " | ".join(vals) + " |")

        count_note = f"Showing {len(rows)} row(s)"
        if len(rows) == effective_limit:
            count_note += f" (limit: {effective_limit})"

        return f"{count_note}:\n\n{header}\n{separator}\n" + "\n".join(data_rows)


# --- Agent construction ---

ALL_TOOLS = [
    list_rules, get_rule, create_rule, update_rule, run_rule, run_all_rules,
    get_error_summary, get_errors, get_run_history,
    search_knowledge, write_knowledge, list_knowledge,
    get_conversation_history, search_conversations,
    list_tables, query_data,
]


def build_agent():
    model = get_chat_model()
    return create_react_agent(model, tools=ALL_TOOLS)


_agent = None
_agent_tool_count = 0


def get_agent():
    global _agent, _agent_tool_count
    if _agent is None or _agent_tool_count != len(ALL_TOOLS):
        _agent = build_agent()
        _agent_tool_count = len(ALL_TOOLS)
    return _agent


async def chat(session_id: str, message: str) -> str:
    """Main entry point: send a message in a conversation and get the agent's response."""
    agent = get_agent()

    async with AppSessionLocal() as session:
        # Load or create conversation
        result = await session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            conversation = Conversation(session_id=session_id)
            session.add(conversation)
            await session.flush()

        # Load message history
        result = await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation.id)
            .order_by(ConversationMessage.created_at)
        )
        history = result.scalars().all()

        # Build message list for the agent
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        messages.append(HumanMessage(content=message))

        # Invoke agent
        result = await agent.ainvoke({"messages": messages})

        # Extract the final assistant response
        response_text = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                response_text = msg.content
                break

        # Save messages
        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
        )
        session.add(user_msg)
        session.add(assistant_msg)

        conversation.last_active_at = datetime.now(timezone.utc)
        await session.commit()

    return response_text
