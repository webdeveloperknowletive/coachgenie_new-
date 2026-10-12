import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.config import settings
from app.models.tenant import Tenant
from app.models.user import User


def make_super_admin_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": "super_admin",
        "email": user.email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def make_owner_token(user: User, tenant_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user.id),
        "tenant_id": str(tenant_id),
        "role": "owner",
        "email": user.email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
async def super_admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="superadmin_control_plane@test.com",
        password_hash="testhash",
        role="super_admin",
        first_name="Platform",
        last_name="SuperAdmin",
        is_active=True,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def sa_headers(super_admin_user: User) -> dict:
    token = make_super_admin_token(super_admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_super_admin_platform_health_probe(
    client: AsyncClient,
    sa_headers: dict,
):
    res = await client.get("/api/v1/platform/health", headers=sa_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["database_status"] == "healthy"
    assert "database_latency_ms" in data
    assert "scheduler_status" in data
    assert "outbox_backlog_count" in data


@pytest.mark.asyncio
async def test_super_admin_platform_ai_config_lifecycle(
    client: AsyncClient,
    sa_headers: dict,
):
    # 1. Get current AI config
    get_res = await client.get("/api/v1/platform/ai/config", headers=sa_headers)
    assert get_res.status_code == 200, get_res.text
    initial = get_res.json()
    assert "active_provider" in initial
    assert "model_routing" in initial

    # 2. Update AI config
    update_payload = {
        "enabled": True,
        "active_provider": "groq",
        "available_providers": ["groq", "openai-compatible"],
        "model_routing": {
            "copilot_model": "llama3-70b-8192",
            "doubt_solver_model": "llama3-70b-8192",
            "career_guidance_model": "llama3-8b-8192",
            "analytics_assistant_model": "llama3-70b-8192",
        },
        "average_latency_ms": 195.0,
    }
    post_res = await client.post("/api/v1/platform/ai/config", json=update_payload, headers=sa_headers)
    assert post_res.status_code == 200, post_res.text
    data = post_res.json()
    assert data["success"] is True
    assert data["config"]["active_provider"] == "groq"


@pytest.mark.asyncio
async def test_super_admin_platform_feature_flags(
    client: AsyncClient,
    sa_headers: dict,
):
    # 1. Get feature flags
    get_res = await client.get("/api/v1/platform/feature-flags", headers=sa_headers)
    assert get_res.status_code == 200, get_res.text
    flags = get_res.json()["features"]
    assert "ai_copilot_enabled" in flags

    # 2. Update feature flags
    post_res = await client.post(
        "/api/v1/platform/feature-flags",
        json={"features": {"beta_features_access": True}},
        headers=sa_headers,
    )
    assert post_res.status_code == 200, post_res.text
    assert post_res.json()["features"]["beta_features_access"] is True


@pytest.mark.asyncio
async def test_super_admin_platform_finance(
    client: AsyncClient,
    sa_headers: dict,
):
    res = await client.get("/api/v1/platform/finance", headers=sa_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "mrr" in data
    assert "arr" in data
    assert "active_subscriptions" in data
    assert "tier_pricing_monthly" in data


@pytest.mark.asyncio
async def test_super_admin_provision_tenant_workspace(
    client: AsyncClient,
    sa_headers: dict,
):
    sub = f"provtest-{uuid.uuid4().hex[:6]}"
    payload = {
        "name": "Provisioned Institute",
        "subdomain": sub,
        "plan": "growth",
        "owner_email": f"owner_{sub}@institute.com",
        "owner_password": "StrongPassword123!",
        "owner_first_name": "Test",
        "owner_last_name": "Owner",
    }
    res = await client.post("/api/v1/platform/tenants", json=payload, headers=sa_headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["success"] is True
    assert data["tenant"]["subdomain"] == sub
    assert data["tenant"]["plan"] == "growth"


@pytest.mark.asyncio
async def test_non_super_admin_rejection_on_platform_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
):
    # Regular owner user
    owner = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"regular_owner_{uuid.uuid4().hex[:4]}@test.com",
        password_hash="testhash",
        role="owner",
        first_name="Reg",
        last_name="Owner",
        is_active=True,
    )
    db_session.add(owner)
    await db_session.commit()

    owner_token = make_owner_token(owner, tenant.id)
    owner_headers = {"Authorization": f"Bearer {owner_token}", "x-tenant-id": str(tenant.id)}

    # Attempt to access health probe
    res_health = await client.get("/api/v1/platform/health", headers=owner_headers)
    assert res_health.status_code == 403

    # Attempt to access AI config
    res_ai = await client.get("/api/v1/platform/ai/config", headers=owner_headers)
    assert res_ai.status_code == 403

    # Attempt to access feature flags
    res_ff = await client.get("/api/v1/platform/feature-flags", headers=owner_headers)
    assert res_ff.status_code == 403

    # Attempt to access finance
    res_fin = await client.get("/api/v1/platform/finance", headers=owner_headers)
    assert res_fin.status_code == 403
