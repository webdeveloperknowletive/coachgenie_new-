import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.tenant import Tenant
from app.models.user import User
from app.models.student import Student
from app.models.batch import Batch, Class, BatchStudent
from app.models.lead import Lead
from app.models.admission import Admission
from app.models.fee import FeeInvoice, FeePayment, FeeInstallment
from app.models.exam import Exam, ExamResult
from app.models.audit import AuditLog
from app.services.financial_engine import (
    to_decimal,
    calculate_installment_schedule,
    create_invoice_installments,
    sync_payment_to_installments,
)
from app.utils.security import hash_password


# ── 1. Financial Integrity & Decimal Precision Tests ─────────────────────────

def test_financial_engine_equal_three_way_installment_split():
    # 100,000 divided by 3 must absorb remainder into the 3rd installment
    total = Decimal("100000.00")
    schedule = calculate_installment_schedule(total_amount=total, installments_count=3, start_date=date(2026, 9, 10))

    assert len(schedule) == 3
    assert schedule[0]["amount_due"] == 33333.33
    assert schedule[1]["amount_due"] == 33333.33
    assert schedule[2]["amount_due"] == 33333.34

    # Exact reconciliation check
    total_calc = sum(Decimal(str(s["amount_due"])) for s in schedule)
    assert total_calc == total


def test_financial_engine_discount_scholarship_and_uneven_split():
    # Total = 65,000, Discount = 5,000, Scholarship = 2,500 -> Net Due = 57,500 over 4 installments
    total = Decimal("65000.00")
    discount = Decimal("5000.00")
    scholarship = Decimal("2500.00")
    net_expected = Decimal("57500.00")

    schedule = calculate_installment_schedule(
        total_amount=total,
        installments_count=4,
        discount=discount,
        scholarship=scholarship,
        start_date=date(2026, 9, 1),
    )

    assert len(schedule) == 4
    # 57,500 / 4 = 14,375.00 each
    for s in schedule:
        assert s["amount_due"] == 14375.00

    total_calc = sum(Decimal(str(s["amount_due"])) for s in schedule)
    assert total_calc == net_expected


@pytest.mark.asyncio
async def test_relational_installments_and_partial_payment_allocation(
    db_session: AsyncSession,
    tenant: Tenant,
    student_user: User,
):
    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        enrollment_no=f"STU-FIN-{uuid.uuid4().hex[:4]}",
        first_name="Finance",
        last_name="Tester",
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    # Invoice for 30,000 in 3 installments (10,000 each)
    invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no=f"INV-FIN-{uuid.uuid4().hex[:4]}",
        amount_due=30000.00,
        amount_paid=0.00,
        due_date=date(2026, 9, 1),
        status="pending",
    )
    db_session.add(invoice)
    await db_session.flush()

    specs = calculate_installment_schedule(30000.00, 3, date(2026, 9, 1))
    await create_invoice_installments(db_session, tenant.id, invoice, specs)

    # 1. Partial Payment of 15,000:
    # - Installment 1 (10,000): fully paid
    # - Installment 2 (10,000): 5,000 paid (partial)
    # - Installment 3 (10,000): 0 paid (pending)
    await sync_payment_to_installments(db_session, invoice, Decimal("15000.00"))

    insts = (await db_session.execute(
        select(FeeInstallment).where(FeeInstallment.invoice_id == invoice.id).order_by(FeeInstallment.installment_no.asc())
    )).scalars().all()

    assert insts[0].status == "paid"
    assert float(insts[0].amount_paid) == 10000.00
    assert insts[1].status == "partial"
    assert float(insts[1].amount_paid) == 5000.00
    assert insts[2].status == "pending"
    assert float(insts[2].amount_paid) == 0.00

    # 2. Second Payment of 15,000:
    # - All installments become 'paid'
    await sync_payment_to_installments(db_session, invoice, Decimal("15000.00"))
    insts_updated = (await db_session.execute(
        select(FeeInstallment).where(FeeInstallment.invoice_id == invoice.id).order_by(FeeInstallment.installment_no.asc())
    )).scalars().all()

    for inst in insts_updated:
        assert inst.status == "paid"
        assert float(inst.amount_paid) == 10000.00


# ── 2. Branded Receipt Generation & IDOR Security Tests ──────────────────────

@pytest.mark.asyncio
async def test_branded_receipt_generation_and_idor_protection(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    student_headers: dict,
    student_user: User,
):
    # Set branding on tenant
    tenant.settings = {
        "branding": {
            "institute_name": "Apex IIT Academy",
            "gstin": "27AAPCA1234A1Z5",
            "phone": "+91 9876543210",
            "address": "123 Education Hub, Pune",
        }
    }
    await db_session.flush()

    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=student_user.id,
        enrollment_no=f"STU-REC-{uuid.uuid4().hex[:4]}",
        first_name="Receipt",
        last_name="Student",
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no=f"INV-REC-{uuid.uuid4().hex[:4]}",
        amount_due=25000.00,
        amount_paid=10000.00,
        due_date=date.today(),
        status="partial",
    )
    db_session.add(invoice)
    await db_session.flush()

    payment = FeePayment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        amount=10000.00,
        payment_mode="upi",
        transaction_ref="UPI-TXN-998877",
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(payment)
    await db_session.flush()

    # 1. Owner requests receipt -> 200 OK with full branding
    rec_res = await client.get(f"/api/v1/fees/payments/{payment.id}/receipt", headers=owner_headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()["data"]
    assert rec_data["institute_name"] == "Apex IIT Academy"
    assert rec_data["gstin"] == "27AAPCA1234A1Z5"
    assert rec_data["amount_paid"] == 10000.00
    assert rec_data["total_amount_due"] == 25000.00
    assert rec_data["balance_remaining"] == 15000.00

    # 2. Linked student requests own receipt -> 200 OK
    st_res = await client.get(f"/api/v1/fees/payments/{payment.id}/receipt", headers=student_headers)
    assert st_res.status_code == 200

    # 3. IDOR: Student attempting to access an unrelated student's payment receipt -> 403 Forbidden
    other_u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"other-student-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Pass123!"),
        role="student",
        first_name="Other",
        last_name="Student",
        is_active=True,
    )
    db_session.add(other_u)
    await db_session.flush()

    other_student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=other_u.id,
        enrollment_no="STU-OTHER-01",
        first_name="Other",
        last_name="Student",
        is_active=True,
    )
    db_session.add(other_student)
    await db_session.flush()

    other_payment = FeePayment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=other_student.id,
        amount=5000.00,
        payment_mode="cash",
    )
    db_session.add(other_payment)
    await db_session.flush()

    idor_res = await client.get(f"/api/v1/fees/payments/{other_payment.id}/receipt", headers=student_headers)
    assert idor_res.status_code == 403


# ── 3. CRM Configurable Pipeline & Deletion Guard Tests ─────────────────────

@pytest.mark.asyncio
async def test_crm_pipeline_configuration_and_deletion_guard(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
):
    # 1. Fetch default pipeline
    res_get = await client.get("/api/v1/leads/pipeline/config", headers=owner_headers)
    assert res_get.status_code == 200
    assert len(res_get.json()["data"]["stages"]) >= 5

    # 2. Update with custom stages
    custom_stages = {
        "stages": [
            {"id": "new", "label": "New Inquiries", "order": 1, "is_system": True},
            {"id": "counselling", "label": "Academic Counselling", "order": 2, "is_system": False},
            {"id": "demo", "label": "Trial Class", "order": 3, "is_system": False},
            {"id": "converted", "label": "Enrolled", "order": 4, "is_system": True},
            {"id": "lost", "label": "Dropped", "order": 5, "is_system": True},
        ],
        "required_documents": [
            {"id": "aadhaar", "name": "Aadhaar Card", "mandatory": True}
        ]
    }
    res_put = await client.put("/api/v1/leads/pipeline/config", json=custom_stages, headers=owner_headers)
    assert res_put.status_code == 200
    assert len(res_put.json()["data"]["stages"]) == 5

    # 3. Create a lead in custom stage 'demo'
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        full_name="Lead In Demo",
        phone="9800000044",
        status="demo",
    )
    db_session.add(lead)
    await db_session.flush()

    # 4. Attempt to remove 'demo' stage while active leads exist in it -> 400 Bad Request
    invalid_stages = {
        "stages": [
            {"id": "new", "label": "New Inquiries", "order": 1, "is_system": True},
            {"id": "counselling", "label": "Academic Counselling", "order": 2, "is_system": False},
            {"id": "converted", "label": "Enrolled", "order": 3, "is_system": True},
            {"id": "lost", "label": "Dropped", "order": 4, "is_system": True},
        ],
        "required_documents": []
    }
    res_del_guard = await client.put("/api/v1/leads/pipeline/config", json=invalid_stages, headers=owner_headers)
    assert res_del_guard.status_code == 400
    assert "cannot delete stage 'demo'" in res_del_guard.json()["message"].lower()


# ── 4. Atomic Admission Conversion & Quota Tests ─────────────────────────────

@pytest.mark.asyncio
async def test_atomic_admission_conversion_and_installment_generation(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    counselor_headers: dict,
):
    # 1. Create Lead
    lead_payload = {
        "full_name": "Convertible Lead",
        "phone": "9800000055",
        "email": "convertible@example.com",
        "parent_name": "Parent Conv",
        "parent_phone": "9800000056",
        "current_class": "10th",
        "grade": "10th",
        "interested_course": "JEE Foundation",
    }
    lead_res = await client.post("/api/v1/leads/", json=lead_payload, headers=counselor_headers)
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["data"]["id"]

    # 2. Convert Lead atomically with fee and 3 installments
    conv_payload = {
        "fee_amount": 45000.00,
        "fee_paid": 15000.00,
        "payment_mode": "upi",
    }
    conv_res = await client.post(f"/api/v1/leads/{lead_id}/convert", json=conv_payload, headers=counselor_headers)
    assert conv_res.status_code in (200, 201)
    res_data = conv_res.json()["data"]
    assert "student_id" in res_data
    student_id = res_data["student_id"]

    # Verify student was created
    student = await db_session.get(Student, uuid.UUID(student_id))
    assert student is not None
    assert student.first_name == "Convertible"

    # Verify invoice was created with installments
    inv = await db_session.scalar(select(FeeInvoice).where(FeeInvoice.student_id == student.id))
    assert inv is not None
    assert float(inv.amount_due) == 45000.00
    assert float(inv.amount_paid) == 15000.00

    # 3. Duplicate conversion rejected
    dup_res = await client.post(f"/api/v1/leads/{lead_id}/convert", json=conv_payload, headers=counselor_headers)
    assert dup_res.status_code in (400, 409)


# ── 5. Rapid Attendance Bulk Entry & Security ────────────────────────────────

@pytest.mark.asyncio
async def test_rapid_attendance_bulk_entry_and_tutor_scope(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    tutor_user: User,
    tutor_headers: dict,
    owner_headers: dict,
):
    # Batch & Class
    batch = Batch(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Attendance Batch",
        academic_year="2026-2027",
    )
    db_session.add(batch)
    await db_session.flush()

    cls = Class(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        tutor_id=tutor_user.id,
        title="Attendance Session 1",
        scheduled_at=datetime.now(timezone.utc),
        room_or_link="Room 101",
    )
    db_session.add(cls)
    await db_session.flush()

    # Enrolled students
    s1 = Student(id=uuid.uuid4(), tenant_id=tenant.id, enrollment_no="STU-ATT-01", first_name="AttOne", last_name="Student", is_active=True)
    s2 = Student(id=uuid.uuid4(), tenant_id=tenant.id, enrollment_no="STU-ATT-02", first_name="AttTwo", last_name="Student", is_active=True)
    db_session.add_all([s1, s2])
    db_session.add_all([
        BatchStudent(batch_id=batch.id, student_id=s1.id, enrolled_at=date.today()),
        BatchStudent(batch_id=batch.id, student_id=s2.id, enrolled_at=date.today()),
    ])
    await db_session.flush()

    # 1. Tutor takes bulk attendance for assigned class
    att_payload = {
        "class_id": str(cls.id),
        "session_date": "2026-09-05",
        "records": [
            {"student_id": str(s1.id), "status": "present"},
            {"student_id": str(s2.id), "status": "absent", "remarks": "Medical leave"},
        ]
    }
    res_att = await client.post("/api/v1/attendance/bulk", json=att_payload, headers=tutor_headers)
    assert res_att.status_code == 200

    # 2. Unassigned class -> Tutor is blocked with 403 Forbidden
    other_tutor = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"other-tutor-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Pass123!"),
        role="tutor",
        first_name="Other",
        last_name="Tutor",
        is_active=True,
    )
    db_session.add(other_tutor)
    await db_session.flush()

    other_cls = Class(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        tutor_id=other_tutor.id,
        title="Other Class",
        scheduled_at=datetime.now(timezone.utc),
        room_or_link="Room 202",
    )
    db_session.add(other_cls)
    await db_session.flush()

    unauth_payload = {
        "class_id": str(other_cls.id),
        "session_date": "2026-09-05",
        "records": [{"student_id": str(s1.id), "status": "present"}]
    }
    res_unauth = await client.post("/api/v1/attendance/bulk", json=unauth_payload, headers=tutor_headers)
    assert res_unauth.status_code == 403


# ── 6. Bulk Exam Marks & Publishing Lifecycle Tests ──────────────────────────

@pytest.mark.asyncio
async def test_bulk_exam_marks_and_publish_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    owner_headers: dict,
    tutor_headers: dict,
    student_headers: dict,
):
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Exam Batch", academic_year="2026-2027")
    db_session.add(batch)
    await db_session.flush()

    s1 = Student(id=uuid.uuid4(), tenant_id=tenant.id, enrollment_no="STU-EX-01", first_name="ExOne", last_name="Stud", is_active=True)
    s2 = Student(id=uuid.uuid4(), tenant_id=tenant.id, enrollment_no="STU-EX-02", first_name="ExTwo", last_name="Stud", is_active=True)
    db_session.add_all([s1, s2])
    await db_session.flush()

    # Create Exam
    exam = Exam(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        batch_id=batch.id,
        title="Physics Unit Test 1",
        total_marks=50,
        passing_marks=20,
        is_published=False,
    )
    db_session.add(exam)
    await db_session.flush()

    # 1. Tutor submits bulk results
    marks_payload = {
        "results": [
            {"student_id": str(s1.id), "marks_obtained": 45, "remarks": "Excellent"},
            {"student_id": str(s2.id), "marks_obtained": 35, "remarks": "Good"},
        ]
    }
    submit_res = await client.post(f"/api/v1/exams/{exam.id}/results", json=marks_payload, headers=tutor_headers)
    assert submit_res.status_code in (200, 201)

    # 2. Student attempts to view unpublished exam results -> 403 Forbidden
    st_view_res = await client.get(f"/api/v1/exams/{exam.id}/results", headers=student_headers)
    assert st_view_res.status_code == 403

    # 3. Owner publishes exam results
    pub_res = await client.post(f"/api/v1/exams/{exam.id}/publish", headers=owner_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["data"]["is_published"] == True

    # 4. Student views published results -> 200 OK
    st_pub_view = await client.get(f"/api/v1/exams/{exam.id}/results", headers=student_headers)
    assert st_pub_view.status_code == 200
    assert len(st_pub_view.json()["data"]) == 2


# ── 7. Tutor Cockpit Workspace Test ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_tutor_faculty_workspace_aggregation(
    client: AsyncClient,
    db_session: AsyncSession,
    tenant: Tenant,
    tutor_user: User,
    tutor_headers: dict,
):
    ws_res = await client.get("/api/v1/tutors/workspace", headers=tutor_headers)
    assert ws_res.status_code == 200
    ws_data = ws_res.json()["data"]
    assert ws_data["tutor_id"] == str(tutor_user.id)
    assert "classes" in ws_data
    assert "batches" in ws_data
    assert "upcoming_exams" in ws_data
