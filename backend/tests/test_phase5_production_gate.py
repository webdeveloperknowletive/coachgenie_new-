import asyncio
import uuid
import time
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.models.tenant import Tenant
from app.models.user import User
from app.models.student import Student
from app.models.batch import Batch, Class
from app.models.fee import FeeInvoice, FeeInstallment, FeePayment
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.automation import AutomationRule, AutomationEvent, AutomationExecution, WebPushSubscription
from app.models.notification import NotificationLog
from app.services.automation_outbox import enqueue_event, claim_events, recover_stale_leases, complete_event
from app.services.automation_engine import (
    upsert_tenant_rule,
    evaluate_attendance_automation,
    evaluate_fee_overdue_automation,
    waive_late_fee,
    process_outbox_batch,
)
from app.services.notification_dispatcher import (
    notification_dispatcher,
    InAppProvider,
    SmtpEmailProvider,
    DeliveryResult,
)
from app.services.entitlement import EntitlementService
from app.utils.security import hash_password


@pytest.fixture
async def parent_user(db_session: AsyncSession, tenant: Tenant) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"parent-gate-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("ParentPass123!"),
        role="parent",
        first_name="Sunil",
        last_name="Verma",
        phone="9876543210",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ── 1. RETRY STATE MACHINE & EXPONENTIAL BACKOFF ────────────────────────────

@pytest.mark.asyncio
async def test_retry_state_machine_and_exponential_backoff(
    db_session: AsyncSession,
    tenant: Tenant,
):
    ev = AutomationEvent(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        event_type="dispatch_notification",
        entity_id=uuid.uuid4(),
        payload={"channel": "in_app", "recipient_id": str(uuid.uuid4())},
        status="CLAIMED",
        retry_count=0,
        max_retries=3,
        scheduled_at=datetime.now(timezone.utc),
    )
    db_session.add(ev)
    await db_session.commit()

    # Attempt 1: Transient failure -> RETRY_WAIT, backoff (2^1 * 30 = 60s)
    await complete_event(db_session, ev, status="FAILED", error_msg="Temporary network glitch", is_transient=True)
    await db_session.commit()
    assert ev.status == "RETRY_WAIT"
    assert ev.retry_count == 1
    assert "Transient failure (attempt 1/3)" in ev.error_msg

    # Attempt 2: Transient failure -> RETRY_WAIT, backoff (2^2 * 30 = 120s)
    await complete_event(db_session, ev, status="FAILED", error_msg="Timeout connecting to peer", is_transient=True)
    await db_session.commit()
    assert ev.status == "RETRY_WAIT"
    assert ev.retry_count == 2

    # Attempt 3: Transient failure -> RETRY_WAIT, backoff (2^3 * 30 = 240s)
    await complete_event(db_session, ev, status="FAILED", error_msg="Timeout connecting to peer", is_transient=True)
    await db_session.commit()
    assert ev.status == "RETRY_WAIT"
    assert ev.retry_count == 3

    # Attempt 4: Max retries exceeded -> Terminal FAILED
    await complete_event(db_session, ev, status="FAILED", error_msg="Server 500 error", is_transient=True)
    await db_session.commit()
    assert ev.status == "FAILED"

    # Permanent failure -> Immediately terminal FAILED without retry
    perm_ev = AutomationEvent(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        event_type="dispatch_notification",
        entity_id=uuid.uuid4(),
        status="CLAIMED",
        retry_count=0,
        max_retries=3,
    )
    db_session.add(perm_ev)
    await db_session.commit()

    await complete_event(db_session, perm_ev, status="FAILED", error_msg="Invalid email address syntax", is_transient=False)
    await db_session.commit()
    assert perm_ev.status == "FAILED"
    assert perm_ev.retry_count == 0  # No useless retry increment


# ── 2. WORKER CRASH & LEASE RECOVERY ────────────────────────────────────────

@pytest.mark.asyncio
async def test_worker_crash_and_lease_recovery_lifecycle(
    db_session: AsyncSession,
    tenant: Tenant,
):
    now = datetime.now(timezone.utc)
    ev = AutomationEvent(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        event_type="attendance_eval",
        entity_id=uuid.uuid4(),
        status="CLAIMED",
        claimed_by="worker-alpha",
        claimed_at=now - timedelta(minutes=15),
        lease_expires_at=now - timedelta(minutes=10),  # Expired lease
        retry_count=0,
        max_retries=3,
        scheduled_at=now - timedelta(minutes=15),
    )
    db_session.add(ev)
    await db_session.commit()

    # Recovery sweep triggers
    recovered = await recover_stale_leases(db_session)
    await db_session.commit()
    assert recovered >= 1

    # Reload event: must be in RETRY_WAIT
    refreshed = (await db_session.execute(select(AutomationEvent).where(AutomationEvent.id == ev.id))).scalar_one()
    assert refreshed.status == "RETRY_WAIT"
    assert refreshed.retry_count == 1

    # Simulate new worker claiming recovered job
    refreshed.scheduled_at = now - timedelta(seconds=5)
    await db_session.commit()

    claimed_by_beta = await claim_events(db_session, worker_id="worker-beta", limit=1)
    await db_session.commit()
    assert len(claimed_by_beta) == 1
    assert claimed_by_beta[0].id == ev.id
    assert claimed_by_beta[0].claimed_by == "worker-beta"


# ── 3. ATTENDANCE MULTI-STEP TRANSITION & COOLDOWN ──────────────────────────

@pytest.mark.asyncio
async def test_attendance_full_crossing_cooldown_and_recovery_cycle(
    db_session: AsyncSession,
    tenant: Tenant,
    parent_user: User,
):
    # Rule: 75% threshold, min 5 sessions, 7 days cooldown
    await upsert_tenant_rule(
        db_session,
        tenant_id=tenant.id,
        rule_type="attendance_alert",
        config={
            "threshold_pct": 75.0,
            "min_sessions": 5,
            "cooldown_days": 7,
            "notify_parent": True,
            "notify_student": False,
            "channel": "in_app",
        },
    )

    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        parent_user_id=parent_user.id,
        enrollment_no="STU-GATE-ATT",
        first_name="Deepak",
        last_name="Joshi",
        is_active=True,
    )
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Batch Gate", academic_year="2026-2027")
    db_session.add_all([student, batch])
    await db_session.flush()

    classes = []
    for i in range(10):
        cls = Class(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            batch_id=batch.id,
            title=f"Gate Session {i+1}",
            scheduled_at=datetime.now(timezone.utc) - timedelta(days=10 - i),
            duration_min=60,
        )
        db_session.add(cls)
        classes.append(cls)
    await db_session.flush()

    # Step 1: 5 sessions, 4 present = 80% (Above 75%) -> 0 alerts
    for i in range(4):
        s = AttendanceSession(id=uuid.uuid4(), tenant_id=tenant.id, class_id=classes[i].id, session_date=date.today() - timedelta(days=10 - i))
        db_session.add(s)
        await db_session.flush()
        db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=s.id, student_id=student.id, status="present"))

    s5 = AttendanceSession(id=uuid.uuid4(), tenant_id=tenant.id, class_id=classes[4].id, session_date=date.today() - timedelta(days=5))
    db_session.add(s5)
    await db_session.flush()
    db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=s5.id, student_id=student.id, status="absent"))
    await db_session.commit()

    # Evaluation at 80%
    alerts_step1 = await evaluate_attendance_automation(db_session, tenant.id, student.id)
    await db_session.commit()
    assert alerts_step1 == 0

    # Step 2: 6th session absent -> 4/6 = 66.7% (Drops below 75%) -> Alert triggered!
    s6 = AttendanceSession(id=uuid.uuid4(), tenant_id=tenant.id, class_id=classes[5].id, session_date=date.today() - timedelta(days=4))
    db_session.add(s6)
    await db_session.flush()
    db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=s6.id, student_id=student.id, status="absent"))
    await db_session.commit()

    alerts_step2 = await evaluate_attendance_automation(db_session, tenant.id, student.id)
    await db_session.commit()
    assert alerts_step2 == 1

    # Step 3: 7th session absent -> 4/7 = 57.1% (Further drop, but within cooldown) -> 0 duplicate alerts
    s7 = AttendanceSession(id=uuid.uuid4(), tenant_id=tenant.id, class_id=classes[6].id, session_date=date.today() - timedelta(days=3))
    db_session.add(s7)
    await db_session.flush()
    db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=s7.id, student_id=student.id, status="absent"))
    await db_session.commit()

    alerts_step3 = await evaluate_attendance_automation(db_session, tenant.id, student.id)
    await db_session.commit()
    assert alerts_step3 == 0


# ── 4. FEE OVERDUE, IMMUNITY, AND EXACT DECIMAL AUDIT ───────────────────────

@pytest.mark.asyncio
async def test_fee_installment_immunity_and_exact_decimal_calculations(
    db_session: AsyncSession,
    tenant: Tenant,
    owner_user: User,
):
    await upsert_tenant_rule(
        db_session,
        tenant_id=tenant.id,
        rule_type="fee_overdue",
        config={
            "grace_period_days": 2,
            "late_fee_type": "percentage",
            "percentage": 5.0,  # 5% late fee
            "max_late_fee": 1000.00,
        },
    )

    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        enrollment_no="STU-FEE-GATE",
        first_name="Ananya",
        last_name="Roy",
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no="INV-GATE-01",
        amount_due=Decimal("15000.00"),
        amount_paid=Decimal("5000.00"),
        due_date=date.today() - timedelta(days=10),
        status="partial",
    )
    db_session.add(invoice)
    await db_session.flush()

    # 1. Overdue Partial Installment (Due ₹5,000, Paid ₹1,000, Outstanding ₹4,000)
    # 5% penalty on ₹4,000 = ₹200.00
    inst_partial = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=1,
        title="Inst 1 Partial",
        amount_due=Decimal("5000.00"),
        amount_paid=Decimal("1000.00"),
        due_date=date.today() - timedelta(days=10),
        status="partial",
    )
    # 2. Overdue Fully Paid Installment (Immune)
    inst_paid = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=2,
        title="Inst 2 Paid",
        amount_due=Decimal("5000.00"),
        amount_paid=Decimal("5000.00"),
        due_date=date.today() - timedelta(days=10),
        status="paid",
    )
    # 3. Cancelled Installment (Immune)
    inst_cancelled = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=3,
        title="Inst 3 Cancelled",
        amount_due=Decimal("5000.00"),
        amount_paid=Decimal("0.00"),
        due_date=date.today() - timedelta(days=10),
        status="cancelled",
    )
    db_session.add_all([inst_partial, inst_paid, inst_cancelled])
    await db_session.commit()

    # Run fee overdue evaluation
    applied = await evaluate_fee_overdue_automation(db_session, tenant.id)
    await db_session.commit()
    assert applied == 1

    # Reload partial installment: 5000 + 200 = 5200.00
    ref_partial = (await db_session.execute(select(FeeInstallment).where(FeeInstallment.id == inst_partial.id))).scalar_one()
    assert ref_partial.amount_due == Decimal("5200.00")

    # Reload paid installment: unchanged at 5000.00
    ref_paid = (await db_session.execute(select(FeeInstallment).where(FeeInstallment.id == inst_paid.id))).scalar_one()
    assert ref_paid.amount_due == Decimal("5000.00")
    assert ref_paid.status == "paid"

    # Reload cancelled installment: unchanged at 5000.00
    ref_cancelled = (await db_session.execute(select(FeeInstallment).where(FeeInstallment.id == inst_cancelled.id))).scalar_one()
    assert ref_cancelled.amount_due == Decimal("5000.00")
    assert ref_cancelled.status == "cancelled"

    # Reload invoice: 15000 + 200 = 15200.00
    ref_inv = (await db_session.execute(select(FeeInvoice).where(FeeInvoice.id == invoice.id))).scalar_one()
    assert ref_inv.amount_due == Decimal("15200.00")


# ── 5. SUSPENDED TENANT SAFETY ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suspended_tenant_automation_safety(
    db_session: AsyncSession,
    tenant: Tenant,
):
    # Create pending event
    ev = await enqueue_event(
        db_session,
        tenant_id=tenant.id,
        event_type="test_suspended",
        entity_id=uuid.uuid4(),
        payload={},
    )
    await db_session.commit()

    # Suspend tenant
    tenant.is_active = False
    await db_session.commit()

    # Worker claim attempt must return 0 jobs for suspended tenant
    claimed = await claim_events(db_session, worker_id="worker-gate", limit=10)
    await db_session.commit()
    assert len(claimed) == 0

    # Reactivate tenant
    tenant.is_active = True
    await db_session.commit()

    # Worker can now claim safely
    claimed_after = await claim_events(db_session, worker_id="worker-gate", limit=10)
    await db_session.commit()
    assert len(claimed_after) >= 1
    assert any(e.id == ev.id for e in claimed_after)


# ── 6. TENANT ISOLATION & IDOR PROTECTION ────────────────────────────────────

@pytest.mark.asyncio
async def test_cross_tenant_automation_isolation(
    client: AsyncClient,
    owner_headers: dict,
    db_session: AsyncSession,
):
    # Other Tenant
    other_tenant = Tenant(
        id=uuid.uuid4(),
        name="Other Institute",
        subdomain=f"other-{uuid.uuid4().hex[:6]}",
        plan="standard",
        is_active=True,
    )
    db_session.add(other_tenant)
    await db_session.flush()

    other_student = Student(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        enrollment_no="STU-OTHER-01",
        first_name="Other",
        last_name="Student",
        is_active=True,
    )
    db_session.add(other_student)
    await db_session.flush()

    other_invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        student_id=other_student.id,
        invoice_no="INV-OTHER-01",
        amount_due=Decimal("1000.00"),
        amount_paid=Decimal("0.00"),
        due_date=date.today(),
        status="pending",
    )
    db_session.add(other_invoice)
    await db_session.flush()

    other_inst = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        invoice_id=other_invoice.id,
        student_id=other_student.id,
        installment_no=1,
        title="Other Inst",
        amount_due=Decimal("1000.00"),
        amount_paid=Decimal("0.00"),
        due_date=date.today(),
        status="pending",
    )
    db_session.add(other_inst)
    await db_session.commit()

    # Malicious attempt to waive other tenant's late fee using current tenant's owner headers
    resp = await client.post(
        "/api/v1/automation/late-fees/waive",
        json={"installment_id": str(other_inst.id), "waiver_amount": 100.0, "reason": "IDOR Attack"},
        headers=owner_headers,
    )
    assert resp.status_code == 404
