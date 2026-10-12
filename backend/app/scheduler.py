import asyncio
import logging
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from app.database import get_db

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"


async def process_outbox_tick():
    """
    Periodic worker tick claiming and processing transactional outbox items.
    """
    from app.services.automation_engine import process_outbox_batch
    async for db in get_db():
        try:
            count = await process_outbox_batch(db, WORKER_ID, limit=50)
            if count > 0:
                logger.info(f"[OUTBOX] Worker {WORKER_ID} processed {count} events")
        except Exception as e:
            logger.error(f"[OUTBOX] Worker error: {e}")


async def recover_leases_tick():
    """
    Periodic recovery of stale leases from crashed worker instances.
    """
    from app.services.automation_outbox import recover_stale_leases
    async for db in get_db():
        try:
            recovered = await recover_stale_leases(db)
            if recovered > 0:
                logger.warning(f"[RECOVERY] Recovered {recovered} stale automation leases")
        except Exception as e:
            logger.error(f"[RECOVERY] Lease recovery error: {e}")


async def run_daily_tenant_automations():
    """
    Daily scheduled sweep evaluating attendance and overdue fee policies across all active tenants.
    """
    from app.models.tenant import Tenant
    from app.services.automation_engine import evaluate_attendance_automation, evaluate_fee_overdue_automation

    async for db in get_db():
        try:
            tenants = (
                await db.execute(select(Tenant).where(Tenant.is_active == True))
            ).scalars().all()

            for t in tenants:
                try:
                    att_alerts = await evaluate_attendance_automation(db, t.id)
                    fee_penalties = await evaluate_fee_overdue_automation(db, t.id)
                    if att_alerts > 0 or fee_penalties > 0:
                        logger.info(
                            f"[AUTOMATION] Tenant {t.subdomain}: "
                            f"{att_alerts} attendance alerts, {fee_penalties} fee penalties"
                        )
                except Exception as te:
                    logger.error(f"[AUTOMATION] Error for tenant {t.id}: {te}")
        except Exception as e:
            logger.error(f"[AUTOMATION] Daily sweep failed: {e}")


# Legacy aliases for backward compatibility
async def notify_overdue_fees():
    await run_daily_tenant_automations()


async def notify_low_attendance():
    await run_daily_tenant_automations()


async def create_default_templates():
    from app.models.notification import NotificationTemplate
    from app.models.tenant import Tenant

    DEFAULT_TEMPLATES = [
        {
            "name": "Fee Due Reminder",
            "channel": "email",
            "subject": "Fee Due — CoachGenie",
            "body": "Dear Parent, your ward {{studentName}}'s fee of ₹{{amount}} was due on {{dueDate}}. Please pay at the earliest.",
            "variables": ["studentName", "amount", "dueDate"],
        },
        {
            "name": "Low Attendance Alert",
            "channel": "email",
            "subject": "Attendance Alert — CoachGenie",
            "body": "Dear Parent, {{studentName}}'s attendance has dropped to {{attendancePercent}}%. Please ensure regular attendance.",
            "variables": ["studentName", "attendancePercent"],
        },
    ]

    async for db in get_db():
        try:
            tenants = (await db.execute(
                select(Tenant).where(Tenant.is_active == True)
            )).scalars().all()

            for tenant in tenants:
                for tpl in DEFAULT_TEMPLATES:
                    existing = (await db.execute(
                        select(NotificationTemplate).where(
                            and_(
                                NotificationTemplate.tenant_id == tenant.id,
                                NotificationTemplate.name == tpl["name"],
                            )
                        )
                    )).scalar_one_or_none()
                    if not existing:
                        db.add(NotificationTemplate(tenant_id=tenant.id, **tpl))

            await db.commit()
            logger.info("[SCHEDULER] Default templates initialized")
        except Exception as e:
            logger.error(f"[SCHEDULER] Template initialization failed: {e}")


def start_scheduler():
    # Outbox worker polling
    scheduler.add_job(
        process_outbox_tick,
        IntervalTrigger(seconds=15),
        id="outbox_worker",
        replace_existing=True,
    )
    # Stale lease recovery
    scheduler.add_job(
        recover_leases_tick,
        IntervalTrigger(seconds=60),
        id="lease_recovery",
        replace_existing=True,
    )
    # Daily automation sweep (at 09:00 UTC)
    scheduler.add_job(
        run_daily_tenant_automations,
        CronTrigger(hour=9, minute=0),
        id="daily_automations",
        replace_existing=True,
    )
    scheduler.start()
    scheduler.add_job(create_default_templates, "date", id="init_templates", replace_existing=True)
    logger.info(f"[SCHEDULER] Started with worker ID {WORKER_ID}")