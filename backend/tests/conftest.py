import pytest
from httpx import ASGITransport, AsyncClient
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings
from app.core.database import MongoSession, close_db, get_async_session, get_mongo_client, init_db
from app.main import app

pytest_plugins = ["tests.fixtures.conftest", "tests.fixtures.auth"]


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> MongoSession:
    original_db = settings.mongodb_db
    settings.mongodb_db = "resumeiq_test"
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        await init_db()
    except Exception as exc:
        pytest.skip(f"MongoDB not available: {exc}")

    yield MongoSession()

    try:
        await get_mongo_client().drop_database("resumeiq_test")
    except Exception:
        pass
    settings.mongodb_db = original_db
    await close_db()
