import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User
from app.utils.security import hash_password


@pytest.fixture
async def super_admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    sa = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"superadmin-{uuid.uuid4().hex[:6]}@coachgenie.com",
        password_hash=hash_password("SuperAdmin123!"),
        role="super_admin",
        first_name="Platform",
        last_name="SuperAdmin",
        is_active=True,
    )
    db_session.add(sa)
    await db_session.commit()
    return sa


# ── 1. CORS TESTS ACROSS LOCAL ORIGINS ────────────────────────────────────────

@pytest.mark.asyncio
async def test_cors_preflight_and_origins(client: AsyncClient):
    allowed_local_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

    for origin in allowed_local_origins:
        # Preflight OPTIONS request
        res = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-Tenant-Subdomain",
            },
        )
        assert res.status_code in (200, 204)
        assert res.headers.get("access-control-allow-origin") == origin

    # Unauthorized origin test
    bad_res = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://malicious-external-site.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert bad_res.headers.get("access-control-allow-origin") != "https://malicious-external-site.com"


# ── 2. SUPER ADMIN LOGIN WITHOUT INSTITUTE CODE ──────────────────────────────

@pytest.mark.asyncio
async def test_super_admin_login_without_institute_code(
    client: AsyncClient,
    super_admin_user: User,
):
    # Super Admin logs in directly without X-Tenant-Subdomain header
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": super_admin_user.email,
            "password": "SuperAdmin123!",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "super_admin"


# ── 3. TENANT USER WITHOUT INSTITUTE CODE PROMPT ─────────────────────────────

@pytest.mark.asyncio
async def test_tenant_user_without_institute_code_requires_code(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
):
    # Regular tenant owner user
    owner = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"instowner-{uuid.uuid4().hex[:6]}@demo.com",
        password_hash=hash_password("OwnerPass123!"),
        role="owner",
        first_name="Institute",
        last_name="Owner",
        is_active=True,
    )
    db_session.add(owner)
    await db_session.commit()

    # Attempt login without X-Tenant-Subdomain
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": owner.email,
            "password": "OwnerPass123!",
        },
    )
    assert res.status_code in (400, 401)
    assert "Institute code" in res.json().get("detail", "") or "Institute code" in res.json().get("message", "")

    # Now login WITH X-Tenant-Subdomain succeeds
    res_with_sub = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-Subdomain": tenant.subdomain},
        json={
            "email": owner.email,
            "password": "OwnerPass123!",
        },
    )
    assert res_with_sub.status_code == 200
    assert res_with_sub.json()["user"]["role"] == "owner"
