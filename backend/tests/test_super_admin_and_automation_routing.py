import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.models.tenant import Tenant
from app.models.user import User
from app.utils.security import hash_password
from app.config import settings


def make_sa_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": "super_admin",
        "email": user.email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def make_user_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "tenantId": str(user.tenant_id),
        "email": user.email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_super_admin_platform_audit_logs_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
):
    # 1. Create Super Admin
    sa = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"superadmin-{uuid.uuid4().hex[:6]}@coachgenie.com",
        password_hash=hash_password("SuperAdmin123!"),
        role="super_admin",
        first_name="Platform",
        last_name="SuperAdmin",
        is_active=True,
        is_verified=True,
    )
    db_session.add(sa)
    await db_session.flush()

    sa_token = make_sa_token(sa)
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # 2. Trigger a plan update as Super Admin which writes an audit log
    plan_res = await client.patch(
        f"/api/v1/platform/tenants/{tenant.id}/plan",
        json={"plan": "enterprise"},
        headers=sa_headers,
    )
    assert plan_res.status_code == 200

    # 3. Query platform audit logs as Super Admin
    audit_res = await client.get("/api/v1/platform/audit-logs", headers=sa_headers)
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert data["success"] is True
    assert data["total"] >= 1
    assert any(log["action"] == "UPDATE_TENANT_PLAN" for log in data["items"])

    # 4. Verify non-super-admin cannot access platform audit logs
    owner = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"owner-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("Admin@123"),
        role="owner",
        first_name="Institute",
        last_name="Owner",
        is_active=True,
        is_verified=True,
    )
    db_session.add(owner)
    await db_session.flush()

    owner_token = make_user_token(owner)
    owner_headers = {
        "Authorization": f"Bearer {owner_token}",
        "X-Tenant-Id": str(tenant.id),
    }

    owner_audit_res = await client.get("/api/v1/platform/audit-logs", headers=owner_headers)
    assert owner_audit_res.status_code == 403


@pytest.mark.asyncio
async def test_automation_rules_persistence_and_eval(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
):
    # 1. Update attendance alert automation rule
    att_payload = {
        "rule_type": "attendance_alert",
        "is_active": True,
        "config": {
            "threshold_pct": 80.0,
            "min_sessions": 6,
            "cooldown_days": 10,
            "notify_parent": True,
            "notify_student": True,
            "channel": "in_app",
        },
    }
    att_res = await client.put(
        "/api/v1/automation/rules/attendance_alert",
        json=att_payload,
        headers=owner_headers,
    )
    assert att_res.status_code == 200
    att_data = att_res.json()
    assert att_data["rule_type"] == "attendance_alert"
    assert att_data["config"]["threshold_pct"] == 80.0
    assert att_data["config"]["min_sessions"] == 6

    # 2. Query rules list
    list_res = await client.get("/api/v1/automation/rules", headers=owner_headers)
    assert list_res.status_code == 200
    rules = list_res.json()
    assert len(rules) >= 1
    saved_rule = next(r for r in rules if r["rule_type"] == "attendance_alert")
    assert saved_rule["config"]["threshold_pct"] == 80.0

    # 3. Trigger manual evaluation
    eval_res = await client.post("/api/v1/automation/trigger-eval", headers=owner_headers)
    assert eval_res.status_code == 200
    assert eval_res.json()["success"] is True

    # 4. Check logs
    logs_res = await client.get("/api/v1/automation/logs", headers=owner_headers)
    assert logs_res.status_code == 200
    assert "data" in logs_res.json()
