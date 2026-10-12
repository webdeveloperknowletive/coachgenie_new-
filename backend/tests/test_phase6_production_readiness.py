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
from app.models.batch import Batch, Class, BatchStudent
from app.models.fee import FeeInvoice, FeeInstallment, FeePayment
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.exam import Exam, ExamResult
from app.core.logging_config import redact_sensitive_dict, StructuredJsonFormatter
from app.services.financial_engine import calculate_installment_schedule
from app.utils.security import hash_password


@pytest.fixture
async def parent_user(db_session: AsyncSession, tenant: Tenant) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"parent-p6-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("ParentPass123!"),
        role="parent",
        first_name="Anil",
        last_name="Kapoor",
        phone="9876543219",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ── 1. HEALTH & READINESS PROBES ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_and_readiness_probes(client: AsyncClient):
    # Liveness probe
    res_health = await client.get("/health")
    assert res_health.status_code == 200
    data_h = res_health.json()
    assert data_h["status"] == "ok"
    assert "password" not in str(data_h)
    assert "postgres" not in str(data_h)

    # Readiness probe
    res_ready = await client.get("/health/ready")
    assert res_ready.status_code == 200
    data_r = res_ready.json()
    assert data_r["status"] == "ready"
    assert "db_url" not in str(data_r)
    assert "secret" not in str(data_r)


# ── 2. STRUCTURED LOGGING & SECRET REDACTION ─────────────────────────────────

def test_structured_log_redaction_engine():
    sensitive_payload = {
        "user_id": "usr-12345",
        "email": "admin@coachgenie.com",
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "rt_secret_token_123",
        "smtp_password": "smtp_pass_key",
        "vapid_private_key": "vapid_sec_abc",
        "nested_details": {
            "api_key": "sk-proj-secret123",
            "safe_counter": 42,
        },
    }

    redacted = redact_sensitive_dict(sensitive_payload)

    assert redacted["user_id"] == "usr-12345"
    assert redacted["email"] == "admin@coachgenie.com"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["refresh_token"] == "[REDACTED]"
    assert redacted["smtp_password"] == "[REDACTED]"
    assert redacted["vapid_private_key"] == "[REDACTED]"
    assert redacted["nested_details"]["api_key"] == "[REDACTED]"
    assert redacted["nested_details"]["safe_counter"] == 42


# ── 3. OPTIMIZED DASHBOARD KPI & ACTION WIDGETS ──────────────────────────────

@pytest.mark.asyncio
async def test_owner_dashboard_kpi_aggregation_and_action_metrics(
    client: AsyncClient,
    owner_headers: dict,
    db_session: AsyncSession,
    tenant: Tenant,
):
    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        enrollment_no="STU-P6-01",
        first_name="Rohan",
        last_name="Gupta",
        is_active=True,
    )
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Batch P6", academic_year="2026-2027", is_active=True)
    db_session.add_all([student, batch])
    await db_session.flush()

    # Create Invoice and Overdue Installment
    inv = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no="INV-P6-01",
        amount_due=Decimal("20000.00"),
        amount_paid=Decimal("5000.00"),
        due_date=date.today() - timedelta(days=5),
        status="partial",
    )
    db_session.add(inv)
    await db_session.flush()

    inst_overdue = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=inv.id,
        student_id=student.id,
        installment_no=1,
        title="Inst Overdue",
        amount_due=Decimal("10000.00"),
        amount_paid=Decimal("5000.00"),
        due_date=date.today() - timedelta(days=5),
        status="overdue",
    )
    db_session.add(inst_overdue)
    await db_session.commit()

    # Call Dashboard Endpoint
    t0 = time.perf_counter()
    resp = await client.get("/api/v1/dashboard/owner", headers=owner_headers)
    t1 = time.perf_counter()

    latency_ms = (t1 - t0) * 1000.0
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Verify canonical metrics
    assert data["total_students"] >= 1
    assert data["active_batches"] >= 1
    assert data["total_revenue"] >= 20000.0
    assert data["total_collected"] >= 5000.0
    assert data["pending_revenue"] >= 15000.0
    assert data["overdue_installments_count"] >= 1
    assert "avg_attendance_percent" in data

    # Performance target check (< 100ms on test environment)
    assert latency_ms < 100.0


# ── 4. COMPLETE END-TO-END PERSONA LIFECYCLE JOURNEY ─────────────────────────

@pytest.mark.asyncio
async def test_complete_e2e_multi_persona_journey(
    client: AsyncClient,
    owner_headers: dict,
    db_session: AsyncSession,
    tenant: Tenant,
    parent_user: User,
):
    """
    E2E Journey:
    1. Admin creates Student & Parent Link
    2. Admin creates Batch & assigns Student
    3. Admin creates Fee Schedule & Installments
    4. Tutor creates Session & records Attendance
    5. Tutor creates Exam & records Result
    6. Student & Parent Portals query aggregated real-data
    """
    # 1. Student Creation
    student_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"stu-e2e-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("StudentPass123!"),
        role="student",
        first_name="Aditi",
        last_name="Nair",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()

    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=student_user.id,
        parent_user_id=parent_user.id,
        enrollment_no="STU-E2E-01",
        first_name="Aditi",
        last_name="Nair",
        email=student_user.email,
        parent_email=parent_user.email,
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    # 2. Batch Creation & Membership
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="JEE Advanced Elite", academic_year="2026-2027", is_active=True)
    db_session.add(batch)
    await db_session.flush()

    db_session.add(BatchStudent(batch_id=batch.id, student_id=student.id))
    await db_session.flush()

    # 3. Fee Installment Schedule Creation
    invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no="INV-E2E-01",
        amount_due=Decimal("12000.00"),
        amount_paid=Decimal("6000.00"),
        due_date=date.today() + timedelta(days=30),
        status="partial",
    )
    db_session.add(invoice)
    await db_session.flush()

    inst1 = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=1,
        title="Term 1",
        amount_due=Decimal("6000.00"),
        amount_paid=Decimal("6000.00"),
        due_date=date.today() - timedelta(days=10),
        status="paid",
    )
    inst2 = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=2,
        title="Term 2",
        amount_due=Decimal("6000.00"),
        amount_paid=Decimal("0.00"),
        due_date=date.today() + timedelta(days=30),
        status="pending",
    )
    db_session.add_all([inst1, inst2])
    await db_session.flush()

    # 4. Class & Attendance
    cls = Class(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Physics - Mechanics",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=1),
        duration_min=60,
    )
    db_session.add(cls)
    await db_session.flush()

    sess = AttendanceSession(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        class_id=cls.id,
        session_date=date.today() - timedelta(days=1),
    )
    db_session.add(sess)
    await db_session.flush()

    db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=sess.id, student_id=student.id, status="present"))

    # 5. Exam & Result
    exam = Exam(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Unit Test 1",
        type="unit_test",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=2),
        total_marks=Decimal("100.00"),
        passing_marks=Decimal("40.00"),
        is_published=True,
    )
    db_session.add(exam)
    await db_session.flush()

    db_session.add(ExamResult(
        tenant_id=tenant.id,
        exam_id=exam.id,
        student_id=student.id,
        marks_obtained=Decimal("88.50"),
        remarks="Excellent",
    ))
    await db_session.commit()

    # 6. Verify Parent Multi-Child Resolution
    from app.services.parent import resolve_authorized_children, get_parent_portal_dashboard
    children = await resolve_authorized_children(db_session, tenant.id, parent_user)
    assert len(children) >= 1
    assert any(c.id == student.id for c in children)

    # 7. Verify Parent Dashboard Aggregation
    p_dash = await get_parent_portal_dashboard(db_session, tenant.id, parent_user, str(student.id))
    assert p_dash["selected_child"]["first_name"] == "Aditi"
    assert p_dash["fees"]["total_paid"] == 6000.0
    assert p_dash["fees"]["balance"] == 6000.0
    assert len(p_dash["exams"]) == 1
    assert p_dash["exams"][0]["marks_obtained"] == 88.5


# ── 5. PERFORMANCE PERCENTILE HARNESS ────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_performance_percentile_benchmark(
    client: AsyncClient,
    owner_headers: dict,
):
    # Warmup request
    await client.get("/api/v1/dashboard/owner", headers=owner_headers)

    latencies = []
    # Execute 15 consecutive requests in warm state
    for _ in range(15):
        t0 = time.perf_counter()
        res = await client.get("/api/v1/dashboard/owner", headers=owner_headers)
        t1 = time.perf_counter()
        assert res.status_code == 200
        latencies.append((t1 - t0) * 1000.0)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]

    print(f"\n[BENCHMARK] /api/v1/dashboard/owner: p50 = {p50:.2f}ms, p95 = {p95:.2f}ms")
    assert p50 < 30.0
    assert p95 < 80.0
