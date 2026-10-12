import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update

from app.models.automation import AutomationEvent
from app.models.tenant import Tenant


async def enqueue_event(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    event_type: str,
    entity_id: str | uuid.UUID,
    payload: dict,
    scheduled_at: Optional[datetime] = None,
    max_retries: int = 3,
) -> AutomationEvent:
    """
    Atomically enqueues an event into the transactional outbox table.
    Enqueued within the same database transaction as the business mutation.
    """
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    e_uuid = uuid.UUID(str(entity_id)) if isinstance(entity_id, str) else entity_id

    event = AutomationEvent(
        tenant_id=t_uuid,
        event_type=event_type,
        entity_id=e_uuid,
        payload=payload,
        status="PENDING",
        max_retries=max_retries,
        scheduled_at=scheduled_at or datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    return event


async def claim_events(
    db: AsyncSession,
    worker_id: str,
    limit: int = 50,
    lease_seconds: int = 300,
) -> List[AutomationEvent]:
    """
    Claims up to `limit` pending or retry-wait events using PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED.
    Safe across multiple concurrent worker instances.
    """
    now = datetime.now(timezone.utc)
    lease_expiration = now + timedelta(seconds=lease_seconds)

    # Find candidate event IDs with row-level locking skipping locked rows
    stmt = (
        select(AutomationEvent.id)
        .join(Tenant, Tenant.id == AutomationEvent.tenant_id)
        .where(
            and_(
                Tenant.is_active == True,
                AutomationEvent.status.in_(["PENDING", "RETRY_WAIT"]),
                AutomationEvent.scheduled_at <= now,
            )
        )
        .order_by(AutomationEvent.scheduled_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(stmt)
    claimed_ids = list(result.scalars().all())

    if not claimed_ids:
        return []

    # Update state to CLAIMED
    upd_stmt = (
        update(AutomationEvent)
        .where(AutomationEvent.id.in_(claimed_ids))
        .values(
            status="CLAIMED",
            claimed_by=worker_id,
            claimed_at=now,
            lease_expires_at=lease_expiration,
        )
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(upd_stmt)
    await db.flush()

    # Retrieve claimed events
    events_stmt = (
        select(AutomationEvent)
        .where(AutomationEvent.id.in_(claimed_ids))
        .order_by(AutomationEvent.scheduled_at.asc())
    )
    events_res = await db.execute(events_stmt)
    return list(events_res.scalars().all())


async def recover_stale_leases(db: AsyncSession) -> int:
    """
    Recovers stale CLAIMED or RUNNING events whose worker lease has expired.
    Transitions them to RETRY_WAIT with an incremented retry counter.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(AutomationEvent)
        .where(
            and_(
                AutomationEvent.status.in_(["CLAIMED", "RUNNING"]),
                AutomationEvent.lease_expires_at <= now,
            )
        )
        .with_for_update(skip_locked=True)
    )
    res = await db.execute(stmt)
    stale_events = list(res.scalars().all())

    recovered_count = 0
    for ev in stale_events:
        ev.retry_count += 1
        if ev.retry_count >= ev.max_retries:
            ev.status = "FAILED"
            ev.error_msg = "Lease expired: worker crashed and maximum retries exceeded."
        else:
            ev.status = "RETRY_WAIT"
            ev.scheduled_at = now + timedelta(seconds=10)
            ev.error_msg = "Recovered from expired lease."
        recovered_count += 1

    if recovered_count > 0:
        await db.flush()

    return recovered_count


async def complete_event(
    db: AsyncSession,
    event: AutomationEvent,
    status: str,
    error_msg: Optional[str] = None,
    is_transient: bool = True,
):
    """
    Transitions an automation event to its terminal or retry state.
    Distinguishes transient failures (retry with exponential backoff) from permanent failures.
    """
    now = datetime.now(timezone.utc)
    if status == "SUCCEEDED":
        event.status = "SUCCEEDED"
        event.error_msg = None
        event.lease_expires_at = None
    elif status == "FAILED":
        if is_transient and event.retry_count < event.max_retries:
            event.retry_count += 1
            event.status = "RETRY_WAIT"
            backoff_sec = (2 ** event.retry_count) * 30
            event.scheduled_at = now + timedelta(seconds=backoff_sec)
            event.error_msg = f"Transient failure (attempt {event.retry_count}/{event.max_retries}): {error_msg}"
        else:
            event.status = "FAILED"
            event.error_msg = error_msg or "Permanent failure."
            event.lease_expires_at = None
    elif status == "CANCELLED":
        event.status = "CANCELLED"
        event.error_msg = error_msg or "Cancelled."
        event.lease_expires_at = None

    await db.flush()
