from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

app_engine = create_async_engine(settings.app_db_url, echo=False)
data_source_engine = create_async_engine(settings.data_source_url, echo=False)

AppSessionLocal = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)
DataSourceSessionLocal = async_sessionmaker(data_source_engine, class_=AsyncSession, expire_on_commit=False)


async def get_app_db():
    async with AppSessionLocal() as session:
        yield session


async def get_data_source():
    async with DataSourceSessionLocal() as session:
        yield session
