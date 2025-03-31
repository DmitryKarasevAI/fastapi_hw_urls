import os
import stat
import pytest_asyncio
import asyncio
from fastapi_cache import FastAPICache
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from types import SimpleNamespace
import uuid
import random
from sqlalchemy import delete
from httpx import AsyncClient, ASGITransport

from src.models import User, Url, Query
from src.database import get_async_session, Base
from src.main import app
from src.auth.users import current_active_user

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_temp.db"

test_engine = create_async_engine(os.environ["DATABASE_URL"], echo=True, future=True)
TestAsyncSessionMaker = async_sessionmaker(test_engine, expire_on_commit=False)


# Creating DB schema for future fixture
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_db_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

    db_path = './test_temp.db'

    try:
        if os.path.exists(db_path):
            os.chmod(db_path, stat.S_IWRITE)
            os.remove(db_path)
    except Exception as e:
        print(f"{e}")


# Overriding dependencies
@pytest_asyncio.fixture(scope="session", autouse=True)
async def override_db_dependency():
    async def _get_test_session():
        async with TestAsyncSessionMaker() as session:
            yield session

    app.dependency_overrides[get_async_session] = _get_test_session
    yield
    app.dependency_overrides.clear()


# Cache fixture
class InMemoryBackend:
    def __init__(self):
        self.store = {}

    async def get(self, key, default=None):
        return self.store.get(key, default)

    async def set(self, key, value, expire=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def clear(self, namespace=None, key=None):
        self.store.clear()

    async def get_with_ttl(self, key):
        return None, self.store.get(key)


@pytest_asyncio.fixture(scope="session", autouse=True)
def override_cache():
    in_memory_backend = InMemoryBackend()
    FastAPICache.init(in_memory_backend, prefix="fastapi-cache-test")


transport = None


# App fixture
@pytest_asyncio.fixture(scope="session")
async def test_app():
    global transport
    transport = ASGITransport(app=app)
    return app


# DB session fixture
@pytest_asyncio.fixture
async def db_session():
    async with TestAsyncSessionMaker() as session:
        yield session


# Fixture for db_cleaning after each test
@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(db_session):
    yield
    await db_session.execute(delete(User))
    await db_session.execute(delete(Query))
    await db_session.execute(delete(Url))
    await db_session.commit()


@pytest_asyncio.fixture
def test_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        email=f"test{random.randint(10000, 99999)}@example.com",
        hashed_password="notapassword",
        is_active=True,
        is_superuser=False
    )


# Authed client fixture
@pytest_asyncio.fixture
async def authed_client(test_user, test_app):
    async with TestAsyncSessionMaker() as session:
        session.add(User(
            id=test_user.id,
            email=test_user.email,
            hashed_password=test_user.hashed_password,
            is_active=test_user.is_active,
            is_superuser=test_user.is_superuser
        ))
        await session.commit()

    test_app.dependency_overrides[current_active_user] = lambda: test_user

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    test_app.dependency_overrides.pop(current_active_user, None)


# Anonymous client fixture
@pytest_asyncio.fixture
async def client(test_app):
    test_app.dependency_overrides.pop(current_active_user, None)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# Event loop
@pytest_asyncio.fixture
def event_loop():
    """Create a fresh event loop for each test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
