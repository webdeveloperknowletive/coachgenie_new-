"""
Shared pytest fixtures for the backend test suite.

Uses a real Postgres test database (see README below) with per-test
transaction rollback for isolation — each test runs inside a SAVEPOINT
that gets rolled back afterward, so tests never leak data into each
other and the DB stays clean without manual cleanup.

Setup (local):
    docker run -d --name coachgenie-test-db -p 5433:5432 \
        -e POSTGRES_PASSWORD=test -e POSTGRES_DB=coachgenie_test postgres:16

    set TEST_DATABASE_URL (PowerShell):
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:test@localhost:5433/coachgenie_test"

Setup (CI): see .github/workflows/ci.yml — a Postgres service container
is provided automatically and TEST_DATABASE_URL is set there.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from jose import jwt

# IMPORTANT: set TEST_DATABASE_URL before importing app.database / app.main,
# since app.database reads DATABASE_URL from env at import time.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:test@localhost:5433/coachgenie_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-local-and-ci-only-not-prod-xxxxx")

from app.database import Base, get_db  # noqa: E402
from app.config import settings  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

# import every model module so Base.metadata is fully populated before
# create_all runs. Must happen BEFORE "from app.main import app" below —
# "import app.models" rebinds the name `app` to the top-level package,
# which would otherwise clobber the FastAPI instance we import next.
import app.models  # noqa: E402,F401

from app.main import app  # noqa: E402  (must be last — see note above)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    Create all tables once for the whole test session, using a
    throwaway engine that's disposed immediately after — this fixture
    only runs schema DDL, it isn't kept alive or reused by tests.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    yield

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_test_db):
    """
    Fresh engine + connection + transaction for THIS test only.
    pytest-asyncio gives every test function its own event loop by
    default, and asyncpg connections are bound to the loop they were
    opened in — so a shared/module-level engine breaks the moment a
    second test tries to reuse connections from the first test's loop
    ("attached to a different loop"). Creating (and disposing) the
    engine fresh inside this fixture guarantees its connections are
    always opened in the current test's own loop.

    The transaction is rolled back on teardown, so nothing a test (or
    the app code it triggers) commits ever persists to the next test.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        yield session

        await session.close()
        await txn.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Authenticated-agnostic async test client wired to the test DB."""

    from app.core.rate_limit import limiter
    limiter.enabled = False
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = False

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def tenant(db_session) -> Tenant:
    t = Tenant(
        id=uuid.uuid4(),
        name="Bright Minds Test Tenant",
        subdomain=f"test-{uuid.uuid4().hex[:8]}",
        plan="basic",
        is_active=True,
        settings={},
    )
    db_session.add(t)
    await db_session.flush()
    return t


async def _make_user(db_session, tenant: Tenant, role: str) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"{role}-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Testpass123!"),
        role=role,
        first_name="Test",
        last_name=role.capitalize(),
        is_active=True,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def owner_user(db_session, tenant) -> User:
    return await _make_user(db_session, tenant, "owner")


@pytest_asyncio.fixture
async def counselor_user(db_session, tenant) -> User:
    return await _make_user(db_session, tenant, "counselor")


@pytest_asyncio.fixture
async def student_user(db_session, tenant) -> User:
    return await _make_user(db_session, tenant, "student")


@pytest_asyncio.fixture
async def tutor_user(db_session, tenant) -> User:
    return await _make_user(db_session, tenant, "tutor")


def make_access_token(user: User, tenant: Tenant) -> str:
    """
    Mirrors app.core.security.create_access_token's payload shape,
    including both tenant_id and tenantId since app.dependencies.py
    checks for either.
    """
    payload = {
        "sub": str(user.id),
        "tenantId": str(tenant.id),
        "tenant_id": str(tenant.id),
        "role": user.role,
        "email": user.email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest_asyncio.fixture
async def owner_headers(owner_user, tenant) -> dict:
    token = make_access_token(owner_user, tenant)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }


@pytest_asyncio.fixture
async def counselor_headers(counselor_user, tenant) -> dict:
    token = make_access_token(counselor_user, tenant)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }


@pytest_asyncio.fixture
async def student_headers(student_user, tenant) -> dict:
    token = make_access_token(student_user, tenant)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }


@pytest_asyncio.fixture
async def tutor_headers(tutor_user, tenant) -> dict:
    token = make_access_token(tutor_user, tenant)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }