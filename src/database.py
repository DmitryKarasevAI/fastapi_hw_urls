import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


_engine = None
_session_maker = None


class Base(DeclarativeBase):
    pass


def get_engine():
    global _engine
    if _engine is None:
        db_url = os.getenv("DATABASE_URL")
        _engine = create_async_engine(db_url, future=True, echo=False)
    return _engine


def get_session_maker():
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_maker


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = get_session_maker()
    async with async_session() as session:
        yield session
