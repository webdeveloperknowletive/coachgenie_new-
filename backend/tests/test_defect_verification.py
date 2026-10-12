import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User
from app.models.student import Student
from app.models.batch import Batch, Class, BatchStudent
from app.models.fee import FeeInvoice
from app.models.exam import Exam, ExamResult
from app.models.notification import NotificationLog
from app.utils.security import create_access_token, hash_password


@pytest.fixture
async def empty_student_user(db_session: AsyncSession, tenant: Tenant) -> tuple[User, Student, dict]:
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"empty-student-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("StudentPass123!"),
        role="student",
        first_name="Empty",
        last_name="Student",
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()

    st = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=u.id,
        enrollment_no=f"STU-{uuid.uuid4().hex[:6]}",
        first_name="Empty",
        last_name="Student",
        email=u.email,
        is_active=True,
    )
    db_session.add(st)
    await db_session.commit()

    token = create_access_token({
        "sub": str(u.id),
        "role": u.role,
        "tenant_id": str(tenant.id),
        "token_type": "access",
    })
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }
    return u, st, headers


# ── 1. STUDENT DASHBOARD EMPTY DATA TEST (DEFECT 1) ───────────────────────────

@pytest.mark.asyncio
async def test_student_dashboard_empty_data_returns_200(
    client: AsyncClient,
    empty_student_user: tuple[User, Student, dict],
):
    _, _, headers = empty_student_user
    res = await client.get("/api/v1/students/portal/dashboard", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    payload = data["data"]
    assert payload["student"]["first_name"] == "Empty"
    assert payload["batches"] == []
    assert payload["today_classes"] == []
    assert payload["fees"]["total_due"] == 0.0
    assert payload["fees"]["total_paid"] == 0.0
    assert payload["fees"]["invoices"] == []
    assert payload["exams"] == []
    assert payload["notifications"] == []


# ── 2. CROSS-STUDENT ACCESS DENIED ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_student_dashboard_ignores_query_params_for_isolation(
    client: AsyncClient,
    empty_student_user: tuple[User, Student, dict],
):
    _, own_student, headers = empty_student_user
    fake_other_id = str(uuid.uuid4())
    # Sending ?student_id=other should NOT leak or switch identity
    res = await client.get(f"/api/v1/students/portal/dashboard?student_id={fake_other_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["student"]["id"] == str(own_student.id)


# ── 3. SUPER ADMIN PLATFORM ENDPOINTS (DEFECT 2) ─────────────────────────────

@pytest.mark.asyncio
async def test_super_admin_platform_metrics(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
):
    sa = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"sa-{uuid.uuid4().hex[:6]}@coachgenie.com",
        password_hash=hash_password("SuperAdmin123!"),
        role="super_admin",
        first_name="Global",
        last_name="SuperAdmin",
        is_active=True,
    )
    db_session.add(sa)
    await db_session.commit()

    token = create_access_token({
        "sub": str(sa.id),
        "role": "super_admin",
        "tenant_id": str(tenant.id),
        "token_type": "access",
    })
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/platform/metrics", headers=headers)
    assert res.status_code == 200
    metrics = res.json()
    assert "total_tenants" in metrics
    assert "active_tenants" in metrics
    assert "total_students" in metrics
    assert "total_staff" in metrics


@pytest.mark.asyncio
async def test_owner_cannot_access_super_admin_platform_metrics(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
):
    owner = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"owner-{uuid.uuid4().hex[:6]}@demo.com",
        password_hash=hash_password("OwnerPass123!"),
        role="owner",
        first_name="Inst",
        last_name="Owner",
        is_active=True,
    )
    db_session.add(owner)
    await db_session.commit()

    token = create_access_token({
        "sub": str(owner.id),
        "role": "owner",
        "tenant_id": str(tenant.id),
        "token_type": "access",
    })
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Subdomain": tenant.subdomain}

    res = await client.get("/api/v1/platform/metrics", headers=headers)
    assert res.status_code == 403
