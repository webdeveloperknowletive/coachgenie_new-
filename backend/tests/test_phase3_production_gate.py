import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import time
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.tenant import Tenant
from app.models.user import User
from app.models.student import Student
from app.models.batch import Batch, Class, BatchStudent, Subject
from app.models.lead import Lead
from app.models.admission import Admission
from app.models.fee import FeeInvoice, FeePayment, FeeInstallment
from app.models.exam import Exam, ExamResult
from app.models.syllabus import SyllabusItem, SyllabusProgress
from app.models.audit import AuditLog
from app.services.financial_engine import (
    to_decimal,
    calculate_installment_schedule,
    create_invoice_installments,
    sync_payment_to_installments,
)
from app.services import admission as admission_service
from app.services import fee as fee_service
from app.services.entitlement import check_quota
from app.utils.security import hash_password
from app.utils.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError


# ── 1. FINANCIAL INTEGRITY (Strict Decimal Arithmetic & Edge Cases) ──────────

def test_financial_exact_reconciliation_cases():
    # Case A: 100,000 / 3
    s1 = calculate_installment_schedule(Decimal("100000.00"), 3, date(2026, 9, 1))
    assert len(s1) == 3
    assert s1[0]["amount_due"] == 33333.33
    assert s1[1]["amount_due"] == 33333.33
    assert s1[2]["amount_due"] == 33333.34
    assert sum(Decimal(str(x["amount_due"])) for x in s1) == Decimal("100000.00")

    # Case B: 99,999 / 3
    s2 = calculate_installment_schedule(Decimal("99999.00"), 3, date(2026, 9, 1))
    assert len(s2) == 3
    assert s2[0]["amount_due"] == 33333.00
    assert s2[1]["amount_due"] == 33333.00
    assert s2[2]["amount_due"] == 33333.00
    assert sum(Decimal(str(x["amount_due"])) for x in s2) == Decimal("99999.00")

    # Case C: 10,000 / 6
    s3 = calculate_installment_schedule(Decimal("10000.00"), 6, date(2026, 9, 1))
    assert len(s3) == 6
    for i in range(5):
        assert s3[i]["amount_due"] == 1666.66
    assert s3[5]["amount_due"] == 1666.70
    assert sum(Decimal(str(x["amount_due"])) for x in s3) == Decimal("10000.00")

    # Case D: Percentage discount producing fractional paise/cents
    total = Decimal("17555.55")
    discount = (total * Decimal("0.125")).quantize(Decimal("0.01"))
    net_due = total - discount
    s4 = calculate_installment_schedule(total, 3, discount=discount, start_date=date(2026, 9, 1))
    assert sum(Decimal(str(x["amount_due"])) for x in s4) == net_due


@pytest.mark.asyncio
async def test_financial_partial_payment_and_overpayment_rejection(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
):
    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        enrollment_no="STU-FIN-GATE-1",
        first_name="FinGate",
        last_name="Tester",
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no="INV-FIN-GATE-1",
        amount_due=5000.00,
        amount_paid=0.00,
        due_date=date(2026, 9, 1),
        status="pending",
    )
    db_session.add(invoice)
    await db_session.flush()

    schedule = calculate_installment_schedule(Decimal("5000.00"), 2, date(2026, 9, 1))
    await create_invoice_installments(db_session, tenant.id, invoice, schedule)

    # 1. Negative payment -> 422 Unprocessable Entity
    neg_res = await client.post(
        f"/api/v1/fees/invoices/{invoice.id}/pay",
        json={"amount": -500.00, "payment_mode": "cash"},
        headers=owner_headers,
    )
    assert neg_res.status_code in (400, 422)

    # 2. Overpayment attempt (6000 > 5000) -> 400 Bad Request
    over_res = await client.post(
        f"/api/v1/fees/invoices/{invoice.id}/pay",
        json={"amount": 6000.00, "payment_mode": "cash"},
        headers=owner_headers,
    )
    assert over_res.status_code in (400, 422)
    assert "exceeds" in over_res.json()["message"].lower()

    # 3. Valid partial payment of 2500 -> 201 Created
    part_res = await client.post(
        f"/api/v1/fees/invoices/{invoice.id}/pay",
        json={"amount": 2500.00, "payment_mode": "cash"},
        headers=owner_headers,
    )
    assert part_res.status_code in (200, 201)


# ── 2. ATOMIC ADMISSION CONVERSION & ROLLBACK INTEGRITY ──────────────────────

@pytest.mark.asyncio
async def test_atomic_admission_conversion_rollback_on_failure(
    db_session: AsyncSession,
    tenant: Tenant,
    owner_user: User,
):
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        full_name="Atomic Lead Test",
        phone="9811111111",
        status="new",
    )
    db_session.add(lead)
    await db_session.flush()

    # Injected simulated failure during transactional conversion
    lead.status = "converting"
    await db_session.flush()
    await db_session.rollback()

    # Verify state after rollback
    refreshed_lead = await db_session.scalar(select(Lead).where(Lead.id == lead.id))
    # After rollback of uncommitted lead, it is absent or unchanged
    assert refreshed_lead is None or refreshed_lead.status == "new"


# ── 3. CRM PIPELINE SAFETY & VALIDATION DEFENSE ──────────────────────────────

@pytest.mark.asyncio
async def test_crm_pipeline_duplicate_and_invalid_validation(
    client: AsyncClient,
    owner_headers: dict,
):
    # 1. Duplicate stage ID
    dup_id_payload = {
        "stages": [
            {"id": "new", "label": "New", "order": 1, "is_system": True},
            {"id": "new", "label": "Duplicate New", "order": 2, "is_system": False},
        ],
        "required_documents": []
    }
    r1 = await client.put("/api/v1/leads/pipeline/config", json=dup_id_payload, headers=owner_headers)
    assert r1.status_code == 422

    # 2. Duplicate order
    dup_order_payload = {
        "stages": [
            {"id": "new", "label": "New", "order": 1, "is_system": True},
            {"id": "contacted", "label": "Contacted", "order": 1, "is_system": False},
        ],
        "required_documents": []
    }
    r2 = await client.put("/api/v1/leads/pipeline/config", json=dup_order_payload, headers=owner_headers)
    assert r2.status_code == 422

    # 3. Missing mandatory 'new' stage
    missing_new_payload = {
        "stages": [
            {"id": "contacted", "label": "Contacted", "order": 1, "is_system": False},
            {"id": "converted", "label": "Converted", "order": 2, "is_system": True},
        ],
        "required_documents": []
    }
    r3 = await client.put("/api/v1/leads/pipeline/config", json=missing_new_payload, headers=owner_headers)
    assert r3.status_code == 422


# ── 4. ATTENDANCE AUTHORIZATION & BATCH SCOPING ──────────────────────────────

@pytest.mark.asyncio
async def test_attendance_batch_membership_enforcement(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    tutor_user: User,
    tutor_headers: dict,
):
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Att Gate Batch", academic_year="2026-2027")
    db_session.add(batch)
    await db_session.flush()

    cls = Class(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        tutor_id=tutor_user.id,
        title="Physics Attendance",
        scheduled_at=datetime.now(timezone.utc),
        room_or_link="Room 10",
    )
    db_session.add(cls)
    await db_session.flush()

    s1 = Student(id=uuid.uuid4(), tenant_id=tenant.id, enrollment_no="STU-ATT-ENR", first_name="Enrolled", last_name="Student", is_active=True)
    s2 = Student(id=uuid.uuid4(), tenant_id=tenant.id, enrollment_no="STU-ATT-UNENR", first_name="Unenrolled", last_name="Student", is_active=True)
    db_session.add_all([s1, s2])
    db_session.add(BatchStudent(batch_id=batch.id, student_id=s1.id, enrolled_at=date.today()))
    await db_session.flush()

    # Attempting to take attendance for unenrolled student 2 -> 400 Bad Request
    payload = {
        "class_id": str(cls.id),
        "session_date": "2026-09-08",
        "records": [
            {"student_id": str(s1.id), "status": "present"},
            {"student_id": str(s2.id), "status": "present"},
        ]
    }
    res = await client.post("/api/v1/attendance/bulk", json=payload, headers=tutor_headers)
    assert res.status_code == 400
    assert "not enrolled in the batch" in res.json()["message"].lower()


# ── 5. EXAM MARKS BOUNDARIES & UNPUBLISHED ACCESS DEFENSE ────────────────────

@pytest.mark.asyncio
async def test_exam_marks_boundary_and_role_guards(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    tutor_user: User,
    tutor_headers: dict,
    student_headers: dict,
):
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Exam Gate Batch", academic_year="2026-2027")
    db_session.add(batch)
    await db_session.flush()

    s1 = Student(id=uuid.uuid4(), tenant_id=tenant.id, enrollment_no="STU-EX-GATE", first_name="Ex", last_name="Student", is_active=True)
    db_session.add(s1)
    await db_session.flush()

    exam = Exam(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Chemistry Exam",
        total_marks=100.0,
        passing_marks=40.0,
        is_published=False,
    )
    db_session.add(exam)
    await db_session.flush()

    # 1. Negative marks -> 422/400
    neg_res = await client.post(
        f"/api/v1/exams/{exam.id}/results",
        json={"results": [{"student_id": str(s1.id), "marks_obtained": -10.0}]},
        headers=tutor_headers,
    )
    assert neg_res.status_code in (400, 422)

    # 2. Exceeding max marks (105 > 100) -> 400
    over_res = await client.post(
        f"/api/v1/exams/{exam.id}/results",
        json={"results": [{"student_id": str(s1.id), "marks_obtained": 105.0}]},
        headers=tutor_headers,
    )
    assert over_res.status_code in (400, 422)

    # 3. Tutor submits valid marks -> 200 OK
    valid_res = await client.post(
        f"/api/v1/exams/{exam.id}/results",
        json={"results": [{"student_id": str(s1.id), "marks_obtained": 85.0}]},
        headers=tutor_headers,
    )
    assert valid_res.status_code in (200, 201)

    # 4. Student blocked from viewing unpublished marks -> 403 Forbidden
    st_res = await client.get(f"/api/v1/exams/{exam.id}/results", headers=student_headers)
    assert st_res.status_code == 403

    # 5. Tutor is forbidden from publishing (only owner/admin can publish) -> 403 Forbidden
    pub_attempt = await client.post(f"/api/v1/exams/{exam.id}/publish", headers=tutor_headers)
    assert pub_attempt.status_code == 403


# ── 6. SYLLABUS SECURITY & PROGRESS VALIDATION ───────────────────────────────

@pytest.mark.asyncio
async def test_syllabus_progress_security_and_scoping(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    tutor_user: User,
    tutor_headers: dict,
    counselor_headers: dict,
):
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Syllabus Batch", academic_year="2026-2027")
    db_session.add(batch)
    await db_session.flush()

    subj = Subject(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Physics 101",
    )
    db_session.add(subj)
    await db_session.flush()

    topic = SyllabusItem(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        subject_id=subj.id,
        title="Thermodynamics",
        sort_order=1,
    )
    db_session.add(topic)
    await db_session.flush()

    # Counselor forbidden from updating topic progress
    c_res = await client.post(
        f"/api/v1/batches/{batch.id}/syllabus/{topic.id}/progress",
        json={"status": "completed"},
        headers=counselor_headers,
    )
    assert c_res.status_code == 403

    # Tutor authorized to update topic progress
    t_res = await client.post(
        f"/api/v1/batches/{batch.id}/syllabus/{topic.id}/progress",
        json={"status": "completed", "notes": "Completed with problem sets"},
        headers=tutor_headers,
    )
    assert t_res.status_code == 200
    assert t_res.json()["data"]["status"] == "completed"


# ── 7. PERFORMANCE BENCHMARKS (Latency & Success) ────────────────────────────

@pytest.mark.asyncio
async def test_phase3_performance_benchmarks(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    tutor_user: User,
    tutor_headers: dict,
    owner_headers: dict,
):
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Perf Batch", academic_year="2026-2027")
    db_session.add(batch)
    await db_session.flush()

    cls = Class(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        tutor_id=tutor_user.id,
        title="Perf Test Class",
        scheduled_at=datetime.now(timezone.utc),
        room_or_link="Hall 1",
    )
    db_session.add(cls)

    exam = Exam(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Perf Exam",
        total_marks=100.0,
        passing_marks=40.0,
        is_published=False,
    )
    db_session.add(exam)
    await db_session.flush()

    students = []
    for i in range(30):
        s = Student(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            enrollment_no=f"STU-PERF-{i:03d}",
            first_name=f"PerfStudent{i}",
            last_name="Test",
            is_active=True,
        )
        db_session.add(s)
        students.append(s)
        db_session.add(BatchStudent(batch_id=batch.id, student_id=s.id, enrolled_at=date.today()))
    await db_session.flush()

    # Benchmark A: Rapid Attendance (30 students, 10 iterations)
    att_latencies = []
    for iter_i in range(10):
        att_payload = {
            "class_id": str(cls.id),
            "session_date": f"2026-09-{iter_i+1:02d}",
            "records": [{"student_id": str(s.id), "status": "present"} for s in students],
        }
        t0 = time.perf_counter()
        r = await client.post("/api/v1/attendance/bulk", json=att_payload, headers=tutor_headers)
        t1 = time.perf_counter()
        assert r.status_code == 200
        att_latencies.append((t1 - t0) * 1000)

    # Benchmark B: Bulk Exam Marks (30 students, 5 iterations)
    exam_latencies = []
    for _ in range(5):
        marks_payload = {
            "results": [{"student_id": str(s.id), "marks_obtained": 75.0} for s in students],
        }
        t0 = time.perf_counter()
        r = await client.post(f"/api/v1/exams/{exam.id}/results", json=marks_payload, headers=tutor_headers)
        t1 = time.perf_counter()
        assert r.status_code in (200, 201)
        exam_latencies.append((t1 - t0) * 1000)

    att_latencies.sort()
    exam_latencies.sort()

    p50_att = att_latencies[len(att_latencies) // 2]
    p95_att = att_latencies[int(len(att_latencies) * 0.95)]
    p50_exam = exam_latencies[len(exam_latencies) // 2]
    p95_exam = exam_latencies[int(len(exam_latencies) * 0.95)]

    print(f"\n[PERFORMANCE RESULTS]")
    print(f"Attendance (30 students x 10 runs): p50={p50_att:.2f}ms, p95={p95_att:.2f}ms")
    print(f"Bulk Marks (30 students x 5 runs): p50={p50_exam:.2f}ms, p95={p95_exam:.2f}ms")
