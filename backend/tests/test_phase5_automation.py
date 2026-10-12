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
from app.models.fee import FeeInvoice, FeePayment, FeeInstallment
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
from app.services.notification_dispatcher import notification_dispatcher
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


# ── 1. DISTRIBUTED JOB CLAIMING & CONCURRENCY ────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_worker_claiming_skip_locked(
    db_session: AsyncSession,
    tenant: Tenant,
):
    # Create 10 pending outbox events
    event_ids = []
    for i in range(10):
        ev = await enqueue_event(
            db_session,
            tenant_id=tenant.id,
            event_type="test_event",
            entity_id=uuid.uuid4(),
            payload={"index": i},
        )
        event_ids.append(ev.id)
    await db_session.commit()

    # Worker 1 claims 5 events
    claimed_w1 = await claim_events(db_session, worker_id="worker-1", limit=5)
    await db_session.commit()

    # Worker 2 claims 5 events
    claimed_w2 = await claim_events(db_session, worker_id="worker-2", limit=5)
    await db_session.commit()

    # Assert mutually disjoint sets (0 double-claims)
    w1_ids = {e.id for e in claimed_w1}
    w2_ids = {e.id for e in claimed_w2}

    assert len(w1_ids) == 5
    assert len(w2_ids) == 5
    assert len(w1_ids.intersection(w2_ids)) == 0
    assert w1_ids.union(w2_ids) == set(event_ids)


@pytest.mark.asyncio
async def test_stale_lease_recovery_and_retry(
    db_session: AsyncSession,
    tenant: Tenant,
):
    now = datetime.now(timezone.utc)
    # Event with expired lease (crashed worker simulation)
    ev = AutomationEvent(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        event_type="test_stale",
        entity_id=uuid.uuid4(),
        status="CLAIMED",
        claimed_by="dead-worker",
        claimed_at=now - timedelta(minutes=10),
        lease_expires_at=now - timedelta(minutes=5),
        retry_count=0,
        max_retries=3,
        scheduled_at=now - timedelta(minutes=10),
    )
    db_session.add(ev)
    await db_session.commit()

    # Recover stale leases
    recovered = await recover_stale_leases(db_session)
    await db_session.commit()
    assert recovered >= 1

    # Reload event
    refreshed = (await db_session.execute(select(AutomationEvent).where(AutomationEvent.id == ev.id))).scalar_one()
    assert refreshed.status == "RETRY_WAIT"
    assert refreshed.retry_count == 1
    assert "Recovered from expired lease" in refreshed.error_msg


# ── 2. TRANSACTIONAL OUTBOX ATOMICITY ────────────────────────────────────────

@pytest.mark.asyncio
async def test_transactional_outbox_rollback_isolation(
    db_session: AsyncSession,
    tenant: Tenant,
):
    ev_id = uuid.uuid4()
    # Rollback simulation
    try:
        ev = AutomationEvent(
            id=ev_id,
            tenant_id=tenant.id,
            event_type="rollback_test",
            entity_id=uuid.uuid4(),
            status="PENDING",
        )
        db_session.add(ev)
        await db_session.flush()
        raise RuntimeError("Simulated transaction crash before commit")
    except RuntimeError:
        await db_session.rollback()

    # Event must NOT exist in database
    res = (await db_session.execute(select(AutomationEvent).where(AutomationEvent.id == ev_id))).scalar_one_or_none()
    assert res is None


# ── 3. ATTENDANCE AUTOMATION & THRESHOLD CROSSING ────────────────────────────

@pytest.mark.asyncio
async def test_attendance_automation_crossing_and_cooldown(
    db_session: AsyncSession,
    tenant: Tenant,
    parent_user: User,
):
    # Configure 80% threshold, min 5 sessions, 7 days cooldown
    await upsert_tenant_rule(
        db_session,
        tenant_id=tenant.id,
        rule_type="attendance_alert",
        config={
            "threshold_pct": 80.0,
            "min_sessions": 5,
            "cooldown_days": 7,
            "notify_parent": True,
            "notify_student": True,
            "channel": "in_app",
        },
    )

    # Student 1: 5 sessions, 3 present = 60% (Below 80%)
    st1 = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        parent_user_id=parent_user.id,
        enrollment_no="STU-ATT-01",
        first_name="Karan",
        last_name="Mehta",
        is_active=True,
    )
    # Student 2: 5 sessions, 5 present = 100% (Above 80%)
    st2 = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        enrollment_no="STU-ATT-02",
        first_name="Pooja",
        last_name="Shah",
        is_active=True,
    )
    db_session.add_all([st1, st2])
    await db_session.flush()

    # Setup Batch and Classes
    batch = Batch(id=uuid.uuid4(), tenant_id=tenant.id, name="Batch Att", academic_year="2026-2027")
    db_session.add(batch)
    await db_session.flush()

    classes = []
    sessions = []
    for i in range(5):
        cls = Class(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            batch_id=batch.id,
            title=f"Session Class {i+1}",
            scheduled_at=datetime.now(timezone.utc) - timedelta(days=5 - i),
            duration_min=60,
        )
        db_session.add(cls)
        classes.append(cls)
    await db_session.flush()

    for i in range(5):
        s = AttendanceSession(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            class_id=classes[i].id,
            session_date=date.today() - timedelta(days=5 - i),
        )
        db_session.add(s)
        sessions.append(s)
    await db_session.flush()

    for i in range(3):
        db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=sessions[i].id, student_id=st1.id, status="present"))
    for i in range(3, 5):
        db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=sessions[i].id, student_id=st1.id, status="absent"))

    for i in range(5):
        db_session.add(AttendanceRecord(tenant_id=tenant.id, session_id=sessions[i].id, student_id=st2.id, status="present"))

    await db_session.commit()

    # Run 1: Alert triggered for Student 1 only
    alerts_1 = await evaluate_attendance_automation(db_session, tenant.id)
    await db_session.commit()
    assert alerts_1 == 1

    # Verify In-App Notification created for parent
    notif = (
        await db_session.execute(
            select(NotificationLog).where(
                and_(
                    NotificationLog.tenant_id == tenant.id,
                    NotificationLog.recipient_id == str(parent_user.id),
                )
            )
        )
    ).scalar_one_or_none()
    assert notif is not None
    assert "60.0%" in notif.body

    # Run 2: Re-running immediately during cooldown -> 0 duplicate alerts
    alerts_2 = await evaluate_attendance_automation(db_session, tenant.id)
    await db_session.commit()
    assert alerts_2 == 0


# ── 4. FEE OVERDUE & DECIMAL LATE-FEE ENGINE ─────────────────────────────────

@pytest.mark.asyncio
async def test_fee_overdue_automation_and_waiver(
    db_session: AsyncSession,
    tenant: Tenant,
    owner_user: User,
):
    # Configure Fee Policy: 3-day grace period, ₹150 fixed late fee, cap ₹500
    await upsert_tenant_rule(
        db_session,
        tenant_id=tenant.id,
        rule_type="fee_overdue",
        config={
            "grace_period_days": 3,
            "late_fee_type": "fixed",
            "late_fee_amount": 150.00,
            "max_late_fee": 500.00,
            "notify_parent": False,
        },
    )

    student = Student(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        enrollment_no="STU-FEE-AUTO",
        first_name="Ravi",
        last_name="Kumar",
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    invoice = FeeInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        student_id=student.id,
        invoice_no="INV-AUTO-01",
        amount_due=Decimal("10000.00"),
        amount_paid=Decimal("0.00"),
        due_date=date.today() - timedelta(days=10),
        status="pending",
    )
    db_session.add(invoice)
    await db_session.flush()

    # Installment 1: Overdue past 3-day grace period (due 10 days ago)
    inst_overdue = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=1,
        title="Term 1",
        amount_due=Decimal("5000.00"),
        amount_paid=Decimal("0.00"),
        due_date=date.today() - timedelta(days=10),
        status="pending",
    )
    # Installment 2: Due in future
    inst_future = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=2,
        title="Term 2",
        amount_due=Decimal("5000.00"),
        amount_paid=Decimal("0.00"),
        due_date=date.today() + timedelta(days=20),
        status="pending",
    )
    # Installment 3: Fully paid (immune)
    inst_paid = FeeInstallment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        student_id=student.id,
        installment_no=3,
        title="Term 3",
        amount_due=Decimal("5000.00"),
        amount_paid=Decimal("5000.00"),
        due_date=date.today() - timedelta(days=10),
        status="paid",
    )
    db_session.add_all([inst_overdue, inst_future, inst_paid])
    await db_session.commit()

    # Run 1: Apply late fee
    penalties = await evaluate_fee_overdue_automation(db_session, tenant.id)
    await db_session.commit()
    assert penalties == 1

    # Reload installment 1: amount_due should be 5000 + 150 = 5150.00
    ref_inst = (await db_session.execute(select(FeeInstallment).where(FeeInstallment.id == inst_overdue.id))).scalar_one()
    assert ref_inst.amount_due == Decimal("5150.00")
    assert ref_inst.status == "overdue"

    # Reload parent invoice: amount_due should be 10000 + 150 = 10150.00
    ref_inv = (await db_session.execute(select(FeeInvoice).where(FeeInvoice.id == invoice.id))).scalar_one()
    assert ref_inv.amount_due == Decimal("10150.00")

    # Run 2: Idempotency check -> 0 duplicate late fees applied
    penalties_2 = await evaluate_fee_overdue_automation(db_session, tenant.id)
    await db_session.commit()
    assert penalties_2 == 0

    # Administrative Waiver: Waive ₹150 penalty
    waived_inst = await waive_late_fee(
        db_session,
        tenant_id=tenant.id,
        installment_id=inst_overdue.id,
        waiver_amount=Decimal("150.00"),
        reason="Medical emergency approved by principal",
        admin_user=owner_user,
    )
    await db_session.commit()
    assert waived_inst.amount_due == Decimal("5000.00")

    # Parent invoice restored to 10000.00
    ref_inv2 = (await db_session.execute(select(FeeInvoice).where(FeeInvoice.id == invoice.id))).scalar_one()
    assert ref_inv2.amount_due == Decimal("10000.00")


# ── 5. NOTIFICATION STATE MACHINE & PROVIDER ISOLATION ───────────────────────

@pytest.mark.asyncio
async def test_notification_provider_isolation_and_unconfigured_smtp(
    db_session: AsyncSession,
    tenant: Tenant,
    monkeypatch,
):
    # InApp Dispatch -> Success
    res_inapp = await notification_dispatcher.dispatch(
        db_session,
        tenant_id=str(tenant.id),
        channel="in_app",
        recipient_id=str(uuid.uuid4()),
        recipient_ref="user@test.com",
        subject="Test InApp",
        body="Hello InApp",
    )
    assert res_inapp.success is True
    assert res_inapp.status == "SENT"

    # SMTP unconfigured -> Returns SKIPPED gracefully without failing business logic
    from app.config import settings
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    res_smtp = await notification_dispatcher.dispatch(
        db_session,
        tenant_id=str(tenant.id),
        channel="email",
        recipient_id=str(uuid.uuid4()),
        recipient_ref="user@test.com",
        subject="Test Email",
        body="Hello Email",
    )
    assert res_smtp.success is True
    assert res_smtp.status == "SKIPPED"


# ── 6. REST API ENDPOINTS & RBAC ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_automation_api_endpoints_and_rbac(
    client: AsyncClient,
    owner_headers: dict,
    student_headers: dict,
    tenant: Tenant,
):
    # 1. Non-owner / Student updating automation rule -> 403 Forbidden
    r1 = await client.put(
        "/api/v1/automation/rules/attendance_alert",
        json={"rule_type": "attendance_alert", "is_active": True, "config": {"threshold_pct": 80.0}},
        headers=student_headers,
    )
    assert r1.status_code == 403

    # 2. Owner updating automation rule -> 200 OK
    r2 = await client.put(
        "/api/v1/automation/rules/attendance_alert",
        json={"rule_type": "attendance_alert", "is_active": True, "config": {"threshold_pct": 85.0, "min_sessions": 5}},
        headers=owner_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["config"]["threshold_pct"] == 85.0

    # 3. Owner triggering manual automation evaluation -> 200 OK
    r3 = await client.post("/api/v1/automation/trigger-eval", headers=owner_headers)
    assert r3.status_code == 200
    assert r3.json()["success"] is True

    # 4. Web push subscribe & unsubscribe -> 200 OK
    r4 = await client.post(
        "/api/v1/notifications/push/subscribe",
        json={"endpoint": "https://push.example.com/sub/123", "p256dh_key": "key123", "auth_key": "auth123"},
        headers=owner_headers,
    )
    assert r4.status_code == 200

    r5 = await client.request(
        "DELETE",
        "/api/v1/notifications/push/unsubscribe?endpoint=https://push.example.com/sub/123",
        headers=owner_headers,
    )
    assert r5.status_code == 200
