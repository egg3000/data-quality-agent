import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from db.session import AppSessionLocal, app_engine, data_source_engine
from routers import chat, errors, knowledge, rules, runs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify database connections on startup
    async with app_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    async with data_source_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    # Seed knowledge base if empty
    try:
        from services.seed_knowledge import seed_knowledge_entries
        async with AppSessionLocal() as session:
            await seed_knowledge_entries(session)
    except Exception as e:
        logger.warning(f"Knowledge base seeding skipped: {e}")

    yield
    await app_engine.dispose()
    await data_source_engine.dispose()


app = FastAPI(
    title="Data Quality Agent",
    description="Rules-based data quality detection and AI agent for ERP master data",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rules.router)
app.include_router(runs.router)
app.include_router(errors.router)
app.include_router(knowledge.router)
app.include_router(chat.router)


@app.get("/health")
async def health_check():
    status = {"status": "ok", "app_db": "disconnected", "data_source": "disconnected"}
    try:
        async with app_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["app_db"] = "connected"
    except Exception:
        status["status"] = "degraded"

    try:
        async with data_source_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["data_source"] = "connected"
    except Exception:
        status["status"] = "degraded"

    return status
