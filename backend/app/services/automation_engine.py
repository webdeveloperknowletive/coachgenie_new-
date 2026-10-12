import uuid
import logging
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload

from app.models.automation import AutomationRule, AutomationEvent, AutomationExecution
from app.models.student import Student
from app.models.user import User
from app.models.attendance import AttendanceRecord
from app.models.fee import FeeInvoice, FeeInstallment
from app.services.automation_outbox import claim_events, complete_event
from app.services.notification_dispatcher import notification_dispatcher
from app.services.audit import log_audit_event
from app.services.financial_engine import to_decimal
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_ATTENDANCE_CONFIG = {
    "threshold_pct": 75.0,
    "min_sessions": 5,
    "cooldown_days": 7,
    "notify_parent": True,
    "notify_student": True,
    "channel": "in_app",
}

DEFAULT_FEE_OVERDUE_CONFIG = {
    "grace_period_days": 3,
    "late_fee_type": "fixed",  # 'none', 'fixed', 'percentage'
    "late_fee_amount": 100.00,
    "max_late_fee": 500.00,
    "notify_parent": True,
    "channel": "in_app",
}


async def get_tenant_rules(db: AsyncSession, tenant_id: str | uuid.UUID) -> List[AutomationRule]:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    stmt = (
        select(AutomationRule)
        .where(
            and_(
                AutomationRule.tenant_id == t_uuid,
                AutomationRule.is_active == True,
            )
        )
        .order_by(AutomationRule.rule_type.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def upsert_tenant_rule(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    rule_type: str,
    config: dict,
    user_id: Optional[uuid.UUID] = None,
) -> AutomationRule:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id

    # Validation
    if rule_type == "attendance_alert":
        thresh = float(config.get("threshold_pct", 75.0))
        if thresh < 10.0 or thresh > 100.0:
            raise ValidationError("threshold_pct must be between 10.0 and 100.0")
        min_s = int(config.get("min_sessions", 5))
        if min_s < 1:
            raise ValidationError("min_sessions must be at least 1")
    elif rule_type in ("fee_overdue", "late_fee"):
        grace = int(config.get("grace_period_days", 3))
        if grace < 0 or grace > 90:
            raise ValidationError("grace_period_days must be between 0 and 90")
        fee_amt = Decimal(str(config.get("late_fee_amount", "0.00")))
        if fee_amt < Decimal("0.00"):
            raise ValidationError("late_fee_amount cannot be negative")

    stmt = select(AutomationRule).where(
        and_(
            AutomationRule.tenant_id == t_uuid,
            AutomationRule.rule_type == rule_type,
            AutomationRule.is_active == True,
        )
    )
    rule = (await db.execute(stmt)).scalar_one_or_none()

    if rule:
        rule.config = config
        rule.updated_by = user_id
        rule.updated_at = datetime.now(timezone.utc)
    else:
        rule = AutomationRule(
            tenant_id=t_uuid,
            rule_type=rule_type,
            is_active=True,
            config=config,
            updated_by=user_id,
        )
        db.add(rule)

    await db.flush()
    return rule


async def evaluate_attendance_automation(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    student_id: Optional[str | uuid.UUID] = None,
) -> int:
    """
    Evaluates attendance rules across students in a tenant.
    Dispatches alerts upon downward threshold crossings while respecting cooldown windows.
    Returns the count of alerts triggered.
    """
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    
    # 1. Fetch active attendance rule
    stmt = select(AutomationRule).where(
        and_(
            AutomationRule.tenant_id == t_uuid,
            AutomationRule.rule_type == "attendance_alert",
            AutomationRule.is_active == True,
        )
    )
    rule = (await db.execute(stmt)).scalar_one_or_none()
    cfg = rule.config if rule else DEFAULT_ATTENDANCE_CONFIG

    threshold_pct = float(cfg.get("threshold_pct", 75.0))
    min_sessions = int(cfg.get("min_sessions", 5))
    cooldown_days = int(cfg.get("cooldown_days", 7))
    notify_parent = bool(cfg.get("notify_parent", True))
    notify_student = bool(cfg.get("notify_student", True))
    channel = cfg.get("channel", "in_app")

    # 2. Query attendance stats
    q = (
        select(
            AttendanceRecord.student_id,
            func.count(AttendanceRecord.id).label("total"),
            func.count(AttendanceRecord.id).filter(AttendanceRecord.status == "present").label("present_count"),
        )
        .where(AttendanceRecord.tenant_id == t_uuid)
        .group_by(AttendanceRecord.student_id)
    )
    if student_id:
        s_uuid = uuid.UUID(str(student_id)) if isinstance(student_id, str) else student_id
        q = q.where(AttendanceRecord.student_id == s_uuid)

    records = (await db.execute(q)).all()

    alerts_triggered = 0
    now = datetime.now(timezone.utc)
    current_month_str = now.strftime("%Y-%m")

    for row in records:
        total = row.total
        present = row.present_count
        if total < min_sessions:
            continue

        pct = round((present / total) * 100.0, 1)
        if pct >= threshold_pct:
            continue  # Normal attendance

        st_id = row.student_id
        idempotency_key = f"att:{t_uuid}:{st_id}:{current_month_str}:{int(threshold_pct)}"

        # Check existing execution & cooldown
        exec_stmt = select(AutomationExecution).where(
            and_(
                AutomationExecution.tenant_id == t_uuid,
                AutomationExecution.idempotency_key == idempotency_key,
            )
        )
        existing_exec = (await db.execute(exec_stmt)).scalar_one_or_none()

        if existing_exec:
            # Check cooldown window
            if existing_exec.executed_at and (now - existing_exec.executed_at) < timedelta(days=cooldown_days):
                continue  # Within cooldown, suppress duplicate alert

        # Fetch student details
        student = (await db.execute(select(Student).where(Student.id == st_id))).scalar_one_or_none()
        if not student:
            continue

        subject = f"Attendance Notice: {student.first_name} {student.last_name}"
        body = (
            f"Attendance Alert: {student.first_name}'s attendance has dropped to {pct}% "
            f"({present}/{total} sessions). Required threshold is {threshold_pct}%."
        )

        # Dispatch to Parent
        if notify_parent and student.parent_user_id:
            await notification_dispatcher.dispatch(
                db, str(t_uuid), channel, str(student.parent_user_id),
                student.parent_email or "parent", subject, body,
            )
        elif notify_parent and student.parent_email:
            await notification_dispatcher.dispatch(
                db, str(t_uuid), "email", str(student.id),
                student.parent_email, subject, body,
            )

        # Dispatch to Student
        if notify_student and student.user_id:
            await notification_dispatcher.dispatch(
                db, str(t_uuid), channel, str(student.user_id),
                student.email or "student", subject, body,
            )

        # Record or update idempotency execution
        if existing_exec:
            existing_exec.executed_at = now
            existing_exec.details = {"attendance_pct": pct, "total": total, "present": present}
        else:
            new_exec = AutomationExecution(
                tenant_id=t_uuid,
                idempotency_key=idempotency_key,
                rule_type="attendance_alert",
                entity_id=st_id,
                status="SUCCEEDED",
                details={"attendance_pct": pct, "total": total, "present": present},
                executed_at=now,
            )
            db.add(new_exec)

        alerts_triggered += 1

    await db.flush()
    return alerts_triggered


async def evaluate_fee_overdue_automation(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
) -> int:
    """
    Evaluates overdue fee installments and applies late fees based on tenant policy.
    Operates strictly on relational FeeInstallment using Decimal financial exactness.
    Returns count of late fees applied.
    """
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id

    # 1. Fetch active fee overdue rule
    stmt = select(AutomationRule).where(
        and_(
            AutomationRule.tenant_id == t_uuid,
            AutomationRule.rule_type.in_(["fee_overdue", "late_fee"]),
            AutomationRule.is_active == True,
        )
    )
    rule = (await db.execute(stmt)).scalar_one_or_none()
    cfg = rule.config if rule else DEFAULT_FEE_OVERDUE_CONFIG

    grace_days = int(cfg.get("grace_period_days", 3))
    late_fee_type = cfg.get("late_fee_type", "fixed")
    late_fee_amount = Decimal(str(cfg.get("late_fee_amount", "100.00")))
    max_late_fee = Decimal(str(cfg.get("max_late_fee", "500.00")))
    notify_parent = bool(cfg.get("notify_parent", True))
    channel = cfg.get("channel", "in_app")

    today = date.today()
    cutoff_date = today - timedelta(days=grace_days)

    # 2. Query overdue pending/partial installments past grace period
    inst_stmt = (
        select(FeeInstallment)
        .options(selectinload(FeeInstallment.student))
        .where(
            and_(
                FeeInstallment.tenant_id == t_uuid,
                FeeInstallment.status.in_(["pending", "partial"]),
                FeeInstallment.due_date <= cutoff_date,
            )
        )
    )
    overdue_installments = list((await db.execute(inst_stmt)).scalars().all())

    late_fees_applied = 0
    now = datetime.now(timezone.utc)

    for inst in overdue_installments:
        if inst.amount_paid >= inst.amount_due:
            continue  # Fully paid guard

        inst_due = Decimal(str(inst.amount_due))
        inst_paid = Decimal(str(inst.amount_paid))
        outstanding = inst_due - inst_paid

        # Calculate penalty
        penalty = Decimal("0.00")
        if late_fee_type == "fixed":
            penalty = late_fee_amount
        elif late_fee_type == "percentage":
            pct = Decimal(str(cfg.get("percentage", "2.0")))
            penalty = to_decimal(outstanding * (pct / Decimal("100.0")))

        if max_late_fee > Decimal("0.00"):
            penalty = min(penalty, max_late_fee)

        idempotency_key = f"late_fee:{t_uuid}:{inst.id}:cycle_1"

        # Check idempotency
        chk_stmt = select(AutomationExecution).where(
            and_(
                AutomationExecution.tenant_id == t_uuid,
                AutomationExecution.idempotency_key == idempotency_key,
            )
        )
        if (await db.execute(chk_stmt)).scalar_one_or_none():
            continue  # Penalty already applied for this cycle

        # Apply late fee to installment and invoice
        if penalty > Decimal("0.00"):
            inst.amount_due = inst_due + penalty
            inst.status = "overdue"

            # Update parent invoice
            inv_stmt = select(FeeInvoice).where(FeeInvoice.id == inst.invoice_id)
            invoice = (await db.execute(inv_stmt)).scalar_one_or_none()
            if invoice:
                invoice.amount_due = Decimal(str(invoice.amount_due)) + penalty
                invoice.status = "overdue"

            # Record Idempotency
            exec_row = AutomationExecution(
                tenant_id=t_uuid,
                idempotency_key=idempotency_key,
                rule_type="late_fee",
                entity_id=inst.id,
                status="SUCCEEDED",
                details={
                    "penalty_applied": float(penalty),
                    "previous_amount_due": float(inst_due),
                    "new_amount_due": float(inst.amount_due),
                },
                executed_at=now,
            )
            db.add(exec_row)

            # Record Audit Log
            await log_audit_event(
                db,
                tenant_id=str(t_uuid),
                action="automation.late_fee_applied",
                entity_type="fee_installment",
                actor_id=None,
                entity_id=str(inst.id),
                metadata={"penalty": float(penalty), "invoice_id": str(inst.invoice_id)},
            )

            # Notification
            student = inst.student
            if student and notify_parent:
                body = (
                    f"Overdue Fee Notice: Installment #{inst.installment_no} of ₹{inst_due} "
                    f"was due on {inst.due_date}. A late penalty of ₹{penalty} has been added."
                )
                if student.parent_user_id:
                    await notification_dispatcher.dispatch(
                        db, str(t_uuid), channel, str(student.parent_user_id),
                        student.parent_email or "parent", "Overdue Fee Alert", body,
                    )

            late_fees_applied += 1

    await db.flush()
    return late_fees_applied


async def waive_late_fee(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    installment_id: str | uuid.UUID,
    waiver_amount: Decimal,
    reason: str,
    admin_user: User,
) -> FeeInstallment:
    """
    Administrative late-fee waiver with auditable reversal.
    """
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    inst_uuid = uuid.UUID(str(installment_id)) if isinstance(installment_id, str) else installment_id

    stmt = select(FeeInstallment).where(
        and_(FeeInstallment.tenant_id == t_uuid, FeeInstallment.id == inst_uuid)
    )
    inst = (await db.execute(stmt)).scalar_one_or_none()
    if not inst:
        raise NotFoundError("FeeInstallment")

    if waiver_amount <= Decimal("0.00"):
        raise ValidationError("Waiver amount must be greater than zero")

    current_due = Decimal(str(inst.amount_due))
    current_paid = Decimal(str(inst.amount_paid))

    if waiver_amount > (current_due - current_paid):
        raise ValidationError("Waiver amount exceeds outstanding installment balance")

    inst.amount_due = current_due - waiver_amount

    # Update parent invoice
    inv = (await db.execute(select(FeeInvoice).where(FeeInvoice.id == inst.invoice_id))).scalar_one_or_none()
    if inv:
        inv.amount_due = Decimal(str(inv.amount_due)) - waiver_amount

    # Audit Trail
    await log_audit_event(
        db,
        tenant_id=str(t_uuid),
        action="fee.late_fee_waived",
        entity_type="fee_installment",
        actor_id=str(admin_user.id),
        entity_id=str(inst.id),
        metadata={
            "waiver_amount": float(waiver_amount),
            "reason": reason,
            "previous_amount_due": float(current_due),
            "new_amount_due": float(inst.amount_due),
        },
    )

    await db.flush()
    return inst


async def process_outbox_batch(
    db: AsyncSession,
    worker_id: str,
    limit: int = 50,
) -> int:
    """
    Worker tick to claim and process outbox events.
    """
    claimed = await claim_events(db, worker_id, limit=limit)
    if not claimed:
        return 0

    processed_count = 0
    for ev in claimed:
        try:
            if ev.event_type == "attendance_eval":
                await evaluate_attendance_automation(db, ev.tenant_id, ev.entity_id)
            elif ev.event_type == "fee_overdue_eval":
                await evaluate_fee_overdue_automation(db, ev.tenant_id)
            elif ev.event_type == "dispatch_notification":
                p = ev.payload
                await notification_dispatcher.dispatch(
                    db, str(ev.tenant_id), p.get("channel", "in_app"),
                    p.get("recipient_id"), p.get("recipient_ref"),
                    p.get("subject"), p.get("body"),
                )

            await complete_event(db, ev, status="SUCCEEDED")
            processed_count += 1
        except Exception as e:
            logger.error(f"[Outbox Worker {worker_id}] Error processing event {ev.id}: {e}", exc_info=True)
            await complete_event(db, ev, status="FAILED", error_msg=str(e), is_transient=True)

    await db.flush()
    return processed_count
