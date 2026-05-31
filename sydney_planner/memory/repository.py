from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from sydney_planner.memory.models import ConversationHistory, UserPreferences


class UserPreferencesRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def get_or_create(self, user_id: str, channel: str) -> UserPreferences:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserPreferences).where(UserPreferences.user_id == user_id)
            )
            prefs = result.scalar_one_or_none()
            if prefs is None:
                prefs = UserPreferences(user_id=user_id, channel=channel)
                session.add(prefs)
                await session.commit()
                await session.refresh(prefs)
            return prefs

    async def update(self, user_id: str, fields: dict) -> UserPreferences:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserPreferences).where(UserPreferences.user_id == user_id)
            )
            prefs = result.scalar_one_or_none()
            if prefs is None:
                raise ValueError(f"No preferences found for user_id={user_id!r}")
            for key, value in fields.items():
                if hasattr(prefs, key):
                    setattr(prefs, key, value)
            await session.commit()
            await session.refresh(prefs)
            return prefs

    async def get_recent_history(self, user_id: str, limit: int = 20) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ConversationHistory)
                .where(ConversationHistory.user_id == user_id)
                .order_by(ConversationHistory.timestamp.desc(), ConversationHistory.id.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
        # Return in chronological order for the messages list
        return [{"role": r.role, "content": r.content} for r in reversed(rows)]

    async def append_history(self, user_id: str, role: str, content: str) -> None:
        async with self._session_factory() as session:
            entry = ConversationHistory(user_id=user_id, role=role, content=content)
            session.add(entry)
            await session.commit()
