from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sydney_planner.memory.models import Base


async def create_engine_and_tables(database_url: str) -> AsyncEngine:
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine
