import asyncio
import uuid
import time
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.tenant import Tenant
from app.models.user import User
from app.models.student import Student
from app.models.batch import Batch, Class, BatchStudent, Subject
from app.models.fee import FeeInvoice, FeePayment, FeeInstallment
from app.models.exam import Exam, ExamResult
from app.models.notification import NotificationLog
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.services.financial_engine import calculate_installment_schedule, create_invoice_installments
from app.utils.security import create_access_token, hash_password


@pytest.fixture
async def parent_user(db_session: AsyncSession, tenant: Tenant) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"parent-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("ParentPass123!"),
        role="parent",
        first_name="Ramesh",
        last_name="Sharma",
        phone="9988776655",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def parent_headers(parent_user: User, tenant: Tenant) -> dict:
    token = create_access_token({
        "sub": str(parent_user.id),
        "role": parent_user.role,
        "tenant_id": str(tenant.id),
        "token_type": "access",
    })
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }


# ── 1. STUDENT PORTAL DASHBOARD & ISOLATION ──────────────────────────────────

@pytest.mark.asyncio
async def test_student_portal_dashboard_session_derived(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    student_user: User,
    student_headers: dict,
):
    # Setup student record linked canonically via user_id
    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=student_user.id,
        enrollment_no="STU-PORTAL-01",
        first_name="Aarav",
        last_name="Verma",
        email=student_user.email,
        phone="9876543210",
        current_class="11th",
        is_active=True,
    )
    db_session.add(student)

    # Setup Batch & Class
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="JEE 2026 Batch", academic_year="2026-2027")
    db_session.add(batch)
    await db_session.flush()

    db_session.add(BatchStudent(batch_id=batch.id, student_id=student.id, enrolled_at=date.today()))
    cls = Class(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Physics Mechanics",
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
        duration_min=60,
    )
    db_session.add(cls)

    # Setup Fee Invoice
    invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no="INV-PORTAL-01",
        amount_due=25000.00,
        amount_paid=10000.00,
        due_date=date.today() + timedelta(days=30),
        status="partial",
    )
    db_session.add(invoice)

    # Setup Published Exam vs Draft Exam
    pub_exam = Exam(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Mechanics Term Exam",
        total_marks=100.0,
        passing_marks=40.0,
        is_published=True,
    )
    draft_exam = Exam(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Draft Quiz",
        total_marks=50.0,
        passing_marks=20.0,
        is_published=False,
    )
    db_session.add_all([pub_exam, draft_exam])
    await db_session.flush()

    db_session.add_all([
        ExamResult(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            exam_id=pub_exam.id,
            student_id=student.id,
            marks_obtained=88.0,
            grade="A",
            rank_in_batch=1,
            is_pass=True,
        ),
        ExamResult(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            exam_id=draft_exam.id,
            student_id=student.id,
            marks_obtained=42.0,
            grade="A",
            rank_in_batch=2,
            is_pass=True,
        ),
    ])
    await db_session.flush()

    # Call Student Dashboard
    res = await client.get("/api/v1/students/portal/dashboard", headers=student_headers)
    assert res.status_code == 200
    data = res.json()["data"]

    # Invariant checks:
    assert data["student"]["id"] == str(student.id)
    assert data["student"]["first_name"] == "Aarav"
    assert len(data["batches"]) == 1
    assert data["fees"]["total_due"] == 25000.0
    assert data["fees"]["total_paid"] == 10000.0
    assert data["fees"]["balance"] == 15000.0
    # Strictly published exams only (draft excluded)
    assert len(data["exams"]) == 1
    assert data["exams"][0]["exam_id"] == str(pub_exam.id)
    assert data["exams"][0]["marks_obtained"] == 88.0


@pytest.mark.asyncio
async def test_student_cross_student_access_denied(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    student_user: User,
    student_headers: dict,
):
    # Student A (authenticated)
    student_a = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=student_user.id,
        enrollment_no="STU-A",
        first_name="StudentA",
        last_name="Test",
        is_active=True,
    )
    # Student B (different student)
    student_b = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        enrollment_no="STU-B",
        first_name="StudentB",
        last_name="Test",
        is_active=True,
    )
    db_session.add_all([student_a, student_b])
    await db_session.flush()

    # 1. Accessing student B profile -> 403
    r1 = await client.get(f"/api/v1/students/{student_b.id}", headers=student_headers)
    assert r1.status_code == 403

    # 2. Accessing student B attendance -> 403
    r2 = await client.get(f"/api/v1/attendance/student/{student_b.id}/summary", headers=student_headers)
    assert r2.status_code == 403

    # 3. Accessing student B exam results -> 403
    r3 = await client.get(f"/api/v1/exams/student/{student_b.id}/results", headers=student_headers)
    assert r3.status_code == 403


# ── 2. PARENT MULTI-CHILD DISCOVERY & SWITCHING ──────────────────────────────

@pytest.mark.asyncio
async def test_parent_multi_child_resolution_and_switching(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    parent_user: User,
    parent_headers: dict,
):
    # Child 1: linked canonically via parent_user_id
    child_1 = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        parent_user_id=parent_user.id,
        enrollment_no="CHILD-01",
        first_name="Rohan",
        last_name="Sharma",
        current_class="10th",
        is_active=True,
    )
    # Child 2: linked via verified parent_email fallback
    child_2 = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        parent_email=parent_user.email,
        enrollment_no="CHILD-02",
        first_name="Priya",
        last_name="Sharma",
        current_class="8th",
        is_active=True,
    )
    # Unrelated child: belongs to another parent
    unrelated_child = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        parent_email="otherparent@test.com",
        enrollment_no="CHILD-OTHER",
        first_name="Stranger",
        last_name="Kid",
        is_active=True,
    )
    db_session.add_all([child_1, child_2, unrelated_child])
    await db_session.flush()

    # 1. Discover authorized children
    c_res = await client.get("/api/v1/parents/children", headers=parent_headers)
    assert c_res.status_code == 200
    children_list = c_res.json()["data"]
    assert len(children_list) == 2
    child_ids = {c["id"] for c in children_list}
    assert str(child_1.id) in child_ids
    assert str(child_2.id) in child_ids
    assert str(unrelated_child.id) not in child_ids

    # 2. Query Dashboard for Child 1
    d1_res = await client.get(f"/api/v1/parents/portal/dashboard?student_id={child_1.id}", headers=parent_headers)
    assert d1_res.status_code == 200
    assert d1_res.json()["data"]["selected_child"]["id"] == str(child_1.id)
    assert d1_res.json()["data"]["selected_child"]["first_name"] == "Rohan"

    # 3. Query Dashboard for Child 2
    d2_res = await client.get(f"/api/v1/parents/portal/dashboard?student_id={child_2.id}", headers=parent_headers)
    assert d2_res.status_code == 200
    assert d2_res.json()["data"]["selected_child"]["id"] == str(child_2.id)
    assert d2_res.json()["data"]["selected_child"]["first_name"] == "Priya"

    # 4. Attempt to query unrelated student ID -> 403 Forbidden
    hack_res = await client.get(f"/api/v1/parents/portal/dashboard?student_id={unrelated_child.id}", headers=parent_headers)
    assert hack_res.status_code == 403
    assert "not linked" in hack_res.json()["message"].lower()


# ── 3. NOTIFICATION INBOX CANONICAL OWNERSHIP ────────────────────────────────

@pytest.mark.asyncio
async def test_notification_inbox_and_read_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    student_user: User,
    student_headers: dict,
    parent_user: User,
    parent_headers: dict,
):
    # Notification for student
    st_notif = NotificationLog(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recipient_id=str(student_user.id),
        channel="in_app",
        recipient_ref=student_user.email,
        subject="Exam Schedule Published",
        body="Physics exam is scheduled for next Monday.",
        status="delivered",
    )
    # Notification for parent
    pt_notif = NotificationLog(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recipient_id=str(parent_user.id),
        channel="in_app",
        recipient_ref=parent_user.email,
        subject="Fee Reminder Term 1",
        body="Term 1 installment of ₹15,000 is due.",
        status="delivered",
    )
    db_session.add_all([st_notif, pt_notif])
    await db_session.flush()

    # 1. Student views inbox -> receives only student notification
    st_inbox = await client.get("/api/v1/notifications/inbox", headers=student_headers)
    assert st_inbox.status_code == 200
    st_items = st_inbox.json()["data"]
    assert len(st_items) == 1
    assert st_items[0]["id"] == str(st_notif.id)

    # 2. Student marks own notification as read -> 200 OK
    read_res = await client.patch(f"/api/v1/notifications/inbox/{st_notif.id}/read", headers=student_headers)
    assert read_res.status_code == 200
    assert read_res.json()["data"]["read_at"] is not None

    # 3. Student attempts to mark parent's notification as read -> 404 Not Found (ownership violation)
    hack_read = await client.patch(f"/api/v1/notifications/inbox/{pt_notif.id}/read", headers=student_headers)
    assert hack_read.status_code == 404


# ── 4. CROSS-TENANT DEFENSE FOR PORTALS ──────────────────────────────────────

@pytest.mark.asyncio
async def test_cross_tenant_portal_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user: User,
    student_headers: dict,
    parent_headers: dict,
):
    # Other Tenant
    tenant_b = Tenant(
        id=uuid.uuid4(),
        name="Tenant B Institute",
        subdomain="tenant-b-unique",
        is_active=True,
    )
    db_session.add(tenant_b)
    await db_session.flush()

    child_in_b = Student(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        enrollment_no="STU-TENANT-B",
        first_name="Alien",
        last_name="Student",
        is_active=True,
    )
    db_session.add(child_in_b)
    await db_session.flush()

    # Parent from Tenant A attempting to access Child in Tenant B -> 403 / 404
    r = await client.get(f"/api/v1/parents/portal/dashboard?student_id={child_in_b.id}", headers=parent_headers)
    assert r.status_code in (403, 404)


# ── 5. PERFORMANCE BENCHMARKS (Portal Aggregation) ───────────────────────────

@pytest.mark.asyncio
async def test_portal_dashboard_performance_benchmarks(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    student_user: User,
    student_headers: dict,
    parent_user: User,
    parent_headers: dict,
):
    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=student_user.id,
        parent_user_id=parent_user.id,
        enrollment_no="STU-PERF-PORTAL",
        first_name="Fast",
        last_name="Student",
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    # Benchmark A: Student Portal Dashboard (10 runs)
    st_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        r = await client.get("/api/v1/students/portal/dashboard", headers=student_headers)
        t1 = time.perf_counter()
        assert r.status_code == 200
        st_times.append((t1 - t0) * 1000)

    # Benchmark B: Parent Portal Dashboard (10 runs)
    pt_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        r = await client.get(f"/api/v1/parents/portal/dashboard?student_id={student.id}", headers=parent_headers)
        t1 = time.perf_counter()
        assert r.status_code == 200
        pt_times.append((t1 - t0) * 1000)

    st_times.sort()
    pt_times.sort()

    p50_st = st_times[len(st_times) // 2]
    p95_st = st_times[int(len(st_times) * 0.95)]
    p50_pt = pt_times[len(pt_times) // 2]
    p95_pt = pt_times[int(len(pt_times) * 0.95)]

    print(f"\n[PHASE 4 PERFORMANCE RESULTS]")
    print(f"Student Portal Dashboard (10 runs): p50={p50_st:.2f}ms, p95={p95_st:.2f}ms")
    print(f"Parent Portal Dashboard (10 runs): p50={p50_pt:.2f}ms, p95={p95_pt:.2f}ms")
