import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.models.tenant import Tenant
from app.models.user import User
from app.models.student import Student
from app.models.batch import Batch
from app.models.fee import FeeInvoice, FeeStructure
from app.models.audit import AuditLog
from app.utils.security import hash_password
from app.config import settings
from tests.conftest import make_access_token


def make_super_admin_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": "super_admin",
        "email": user.email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


import pytest_asyncio


@pytest_asyncio.fixture
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
        is_verified=True,
    )
    db_session.add(sa)
    await db_session.flush()
    return sa


@pytest.fixture
async def super_admin_headers(super_admin_user: User) -> dict:
    token = make_super_admin_token(super_admin_user)
    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.mark.asyncio
async def test_super_admin_security_and_non_admin_rejection(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    counselor_headers: dict,
    super_admin_headers: dict,
):
    # 1. Unauthenticated request -> 401
    res_unauth = await client.get("/api/v1/platform/metrics")
    assert res_unauth.status_code == 401

    # 2. Tenant Owner request -> 403 Forbidden
    res_owner = await client.get("/api/v1/platform/metrics", headers=owner_headers)
    assert res_owner.status_code == 403

    # 3. Counselor request -> 403 Forbidden
    res_counselor = await client.get("/api/v1/platform/metrics", headers=counselor_headers)
    assert res_counselor.status_code == 403

    # 4. Super Admin request -> 200 OK
    res_sa = await client.get("/api/v1/platform/metrics", headers=super_admin_headers)
    assert res_sa.status_code == 200
    metrics = res_sa.json()
    assert "total_tenants" in metrics
    assert "active_tenants" in metrics
    assert "plan_distribution" in metrics


@pytest.mark.asyncio
async def test_tenant_lifecycle_and_plan_upgrade(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    super_admin_headers: dict,
):
    tenant_id_str = str(tenant.id)

    # 1. View tenant details and entitlements
    view_res = await client.get(f"/api/v1/platform/tenants/{tenant_id_str}", headers=super_admin_headers)
    assert view_res.status_code == 200
    detail = view_res.json()
    assert detail["tenant"]["id"] == tenant_id_str
    assert "quotas" in detail["entitlements"]
    assert detail["entitlements"]["quotas"]["max_students"] == 100  # starter base

    # 2. Update Plan to Growth
    plan_res = await client.patch(
        f"/api/v1/platform/tenants/{tenant_id_str}/plan",
        json={"plan": "growth"},
        headers=super_admin_headers,
    )
    assert plan_res.status_code == 200
    assert plan_res.json()["plan"] == "growth"

    # Verify updated quotas reflect Growth plan (500 students)
    view_growth = await client.get(f"/api/v1/platform/tenants/{tenant_id_str}", headers=super_admin_headers)
    assert view_growth.json()["entitlements"]["quotas"]["max_students"] == 500

    # 3. Apply Enterprise Custom Quota Override
    override_res = await client.patch(
        f"/api/v1/platform/tenants/{tenant_id_str}/quotas",
        json={"max_students": 2500, "max_batches": 150},
        headers=super_admin_headers,
    )
    assert override_res.status_code == 200
    assert override_res.json()["plan_overrides"]["quotas"]["max_students"] == 2500

    # 4. Suspend Tenant
    suspend_res = await client.post(f"/api/v1/platform/tenants/{tenant_id_str}/suspend", headers=super_admin_headers)
    assert suspend_res.status_code == 200

    # 5. Reactivate Tenant
    activate_res = await client.post(f"/api/v1/platform/tenants/{tenant_id_str}/activate", headers=super_admin_headers)
    assert activate_res.status_code == 200


@pytest.mark.asyncio
async def test_server_side_quota_enforcement(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    super_admin_headers: dict,
):
    tenant_id_str = str(tenant.id)

    # Set strict student quota override of 2 students on this test tenant
    await client.patch(
        f"/api/v1/platform/tenants/{tenant_id_str}/quotas",
        json={"max_students": 2},
        headers=super_admin_headers,
    )

    # Student 1 creation -> OK
    s1 = {
        "enrollment_no": f"STU-Q1-{uuid.uuid4().hex[:4]}",
        "first_name": "Student",
        "last_name": "One",
        "email": f"stu1-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9800000001",
        "parent_name": "Parent One",
        "parent_phone": "9800000002",
        "current_class": "10th",
    }
    r1 = await client.post("/api/v1/students/", json=s1, headers=owner_headers)
    assert r1.status_code == 201

    # Student 2 creation -> OK
    s2 = {
        "enrollment_no": f"STU-Q2-{uuid.uuid4().hex[:4]}",
        "first_name": "Student",
        "last_name": "Two",
        "email": f"stu2-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9800000003",
        "parent_name": "Parent Two",
        "parent_phone": "9800000004",
        "current_class": "10th",
    }
    r2 = await client.post("/api/v1/students/", json=s2, headers=owner_headers)
    assert r2.status_code == 201

    # Student 3 creation -> Quota Exceeded (403 Forbidden)
    s3 = {
        "enrollment_no": f"STU-Q3-{uuid.uuid4().hex[:4]}",
        "first_name": "Student",
        "last_name": "Three",
        "email": f"stu3-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9800000005",
        "parent_name": "Parent Three",
        "parent_phone": "9800000006",
        "current_class": "10th",
    }
    r3 = await client.post("/api/v1/students/", json=s3, headers=owner_headers)
    assert r3.status_code == 403
    err_msg = r3.json().get("message") or r3.json().get("detail", "")
    assert "quota limit reached" in err_msg.lower()


@pytest.mark.asyncio
async def test_diagnostic_impersonation_mode_and_audit(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_user: User,
    super_admin_user: User,
    super_admin_headers: dict,
):
    tenant_id_str = str(tenant.id)

    # 1. Super admin issues diagnostic impersonation token for tenant
    imp_res = await client.post(
        f"/api/v1/platform/impersonate/{tenant_id_str}",
        headers=super_admin_headers,
    )
    assert imp_res.status_code == 200
    imp_data = imp_res.json()
    assert "token" in imp_data
    assert imp_data["expires_in_seconds"] == 900
    assert imp_data["impersonated_email"] == owner_user.email

    diag_token = imp_data["token"]
    diag_headers = {
        "Authorization": f"Bearer {diag_token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }

    # 2. Use diagnostic token to access tenant workspace (read-only / troubleshooting)
    stu_res = await client.get("/api/v1/students/", headers=diag_headers)
    assert stu_res.status_code == 200

    # 3. Verify diagnostic token CANNOT invoke Super Admin platform endpoints
    diag_sa_blocked = await client.get("/api/v1/platform/metrics", headers=diag_headers)
    assert diag_sa_blocked.status_code == 403

    # 4. Verify audit log was written for this impersonation
    audit_res = await client.get(
        f"/api/v1/audit-logs/?action=DIAGNOSTIC_IMPERSONATION",
        headers=diag_headers,
    )
    assert audit_res.status_code == 200
    assert audit_res.json()["total"] >= 1


@pytest.mark.asyncio
async def test_batch_and_staff_quota_enforcement(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    super_admin_headers: dict,
):
    tenant_id_str = str(tenant.id)

    # Set batch quota = 1 and staff quota = 1 (owner counts as 1 staff)
    await client.patch(
        f"/api/v1/platform/tenants/{tenant_id_str}/quotas",
        json={"max_batches": 1, "max_staff": 1},
        headers=super_admin_headers,
    )

    # 1. Batch 1 creation -> OK
    b1 = {
        "name": f"Batch Alpha-{uuid.uuid4().hex[:4]}",
        "academic_year": "2026-2027",
        "capacity": 30,
    }
    r1 = await client.post("/api/v1/batches/", json=b1, headers=owner_headers)
    assert r1.status_code == 201

    # 2. Batch 2 creation -> Exceeds batch quota (403 Forbidden)
    b2 = {
        "name": f"Batch Beta-{uuid.uuid4().hex[:4]}",
        "academic_year": "2026-2027",
        "capacity": 30,
    }
    r2 = await client.post("/api/v1/batches/", json=b2, headers=owner_headers)
    assert r2.status_code == 403

    # 3. Staff user creation -> Owner already consumes 1 staff slot, so adding 2nd staff fails
    staff_payload = {
        "email": f"tutor-{uuid.uuid4().hex[:6]}@example.com",
        "password": "Password123!",
        "first_name": "Tutor",
        "last_name": "User",
        "role": "tutor",
    }
    r_staff = await client.post("/api/v1/auth/register-staff", json=staff_payload, headers=owner_headers)
    assert r_staff.status_code == 403


@pytest.mark.asyncio
async def test_suspended_tenant_operations_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    super_admin_headers: dict,
):
    tenant_id_str = str(tenant.id)

    # Suspend tenant
    await client.post(f"/api/v1/platform/tenants/{tenant_id_str}/suspend", headers=super_admin_headers)

    # Attempt to create a student in suspended tenant -> 403 Forbidden
    stu_payload = {
        "enrollment_no": f"STU-SUS-{uuid.uuid4().hex[:4]}",
        "first_name": "Suspended",
        "last_name": "Student",
        "email": f"susp-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9800000099",
        "current_class": "10th",
    }
    res = await client.post("/api/v1/students/", json=stu_payload, headers=owner_headers)
    assert res.status_code == 403
    err_msg = res.json().get("message") or res.json().get("detail", "")
    assert "suspended" in err_msg.lower()


@pytest.mark.asyncio
async def test_diagnostic_mode_strictly_read_only_and_mutation_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_user: User,
    super_admin_headers: dict,
):
    tenant_id_str = str(tenant.id)

    # 1. Obtain diagnostic token
    imp_res = await client.post(f"/api/v1/platform/impersonate/{tenant_id_str}", headers=super_admin_headers)
    diag_token = imp_res.json()["token"]
    diag_headers = {
        "Authorization": f"Bearer {diag_token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }

    # 2. GET is permitted
    get_res = await client.get("/api/v1/students/", headers=diag_headers)
    assert get_res.status_code == 200

    # 3. POST is blocked with 403 Forbidden (Read-only restriction)
    post_res = await client.post(
        "/api/v1/students/",
        json={"enrollment_no": "TEST-DIAG-01", "first_name": "Diag", "last_name": "Blocked"},
        headers=diag_headers,
    )
    assert post_res.status_code == 403
    assert "read-only" in (post_res.json().get("message") or "").lower()

    # 4. PATCH/DELETE blocked
    patch_res = await client.patch(f"/api/v1/roles/{uuid.uuid4()}", json={"name": "Hacked"}, headers=diag_headers)
    assert patch_res.status_code == 403


@pytest.mark.asyncio
async def test_plan_downgrade_grandfathering_safety(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    super_admin_headers: dict,
):
    tenant_id_str = str(tenant.id)

    # 1. Start with Growth plan (max 500 students) and create 2 students
    await client.patch(
        f"/api/v1/platform/tenants/{tenant_id_str}/plan",
        json={"plan": "growth"},
        headers=super_admin_headers,
    )
    s1 = {
        "enrollment_no": f"STU-GA-{uuid.uuid4().hex[:4]}",
        "first_name": "Student",
        "last_name": "Alpha",
        "email": f"stuga-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9800000011",
        "current_class": "10th",
    }
    s2 = {
        "enrollment_no": f"STU-GB-{uuid.uuid4().hex[:4]}",
        "first_name": "Student",
        "last_name": "Beta",
        "email": f"stugb-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9800000012",
        "current_class": "10th",
    }
    r1 = await client.post("/api/v1/students/", json=s1, headers=owner_headers)
    r2 = await client.post("/api/v1/students/", json=s2, headers=owner_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201

    # 2. Downgrade plan / set quota to 1 student (current count is 2)
    await client.patch(
        f"/api/v1/platform/tenants/{tenant_id_str}/quotas",
        json={"max_students": 1},
        headers=super_admin_headers,
    )

    # 3. Grandfathering verification: existing 2 students are NOT deleted and remain fully accessible
    list_res = await client.get("/api/v1/students/", headers=owner_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 2

    # 4. New student creation is blocked (quota exceeded)
    s3 = {
        "enrollment_no": f"STU-GC-{uuid.uuid4().hex[:4]}",
        "first_name": "Student",
        "last_name": "Gamma",
        "email": f"stugc-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9800000013",
        "current_class": "10th",
    }
    r3 = await client.post("/api/v1/students/", json=s3, headers=owner_headers)
    assert r3.status_code == 403


@pytest.mark.asyncio
async def test_enterprise_override_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    super_admin_headers: dict,
):
    # Create Tenant B
    tenant_b = Tenant(
        id=uuid.uuid4(),
        name="Tenant B Isolation Test",
        subdomain=f"iso-b-{uuid.uuid4().hex[:6]}",
        plan="enterprise",
        is_active=True,
        settings={},
    )
    db_session.add(tenant_b)
    await db_session.flush()

    tenant_a_id = str(tenant.id)
    tenant_b_id = str(tenant_b.id)

    # Apply override to Tenant A ONLY: max_students = 12000
    await client.patch(
        f"/api/v1/platform/tenants/{tenant_a_id}/quotas",
        json={"max_students": 12000},
        headers=super_admin_headers,
    )

    # Fetch Tenant A entitlements -> max_students = 12000
    res_a = await client.get(f"/api/v1/platform/tenants/{tenant_a_id}", headers=super_admin_headers)
    assert res_a.json()["entitlements"]["quotas"]["max_students"] == 12000

    # Fetch Tenant B entitlements -> max_students = 5000 (standard Enterprise default)
    res_b = await client.get(f"/api/v1/platform/tenants/{tenant_b_id}", headers=super_admin_headers)
    assert res_b.json()["entitlements"]["quotas"]["max_students"] == 5000
