import logging
import uuid
from typing import Any, Dict, Optional
from datetime import datetime
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog

logger = logging.getLogger("coaching_erp")

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "token_hash",
    "secret",
    "secret_key",
    "otp",
    "otp_hash",
}


def sanitize_metadata(data: Any) -> Any:
    """Recursively strip sensitive keys (passwords, tokens, secrets) before audit logging."""
    if not isinstance(data, dict):
        return data
    cleaned = {}
    for k, v in data.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            cleaned[k] = "[REDACTED]"
        elif isinstance(v, dict):
            cleaned[k] = sanitize_metadata(v)
        elif isinstance(v, list):
            cleaned[k] = [sanitize_metadata(item) if isinstance(item, dict) else item for item in v]
        else:
            cleaned[k] = v
    return cleaned


async def log_audit_event(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    action: str,
    entity_type: str,
    actor_id: str | uuid.UUID | None = None,
    entity_id: str | None = None,
    ip_address: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Non-destructive audit logging service."""
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    a_uuid = uuid.UUID(str(actor_id)) if actor_id else None

    clean_meta = sanitize_metadata(metadata) if metadata else {}

    audit_entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=t_uuid,
        actor_id=a_uuid,
        action=action.upper(),
        entity_type=entity_type.lower(),
        entity_id=str(entity_id) if entity_id else None,
        ip_address=ip_address,
        metadata_=clean_meta,
    )
    db.add(audit_entry)
    # Use flush so the record is queued within transaction without committing prematurely
    try:
        await db.flush()
    except Exception as e:
        logger.warning(f"Audit log flush warning: {e}")
    return audit_entry


async def get_audit_logs(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    page: int = 1,
    limit: int = 20,
    actor_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> dict:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    conditions = [AuditLog.tenant_id == t_uuid]

    if actor_id:
        conditions.append(AuditLog.actor_id == uuid.UUID(str(actor_id)))
    if action:
        conditions.append(AuditLog.action == action.upper())
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type.lower())
    if from_date:
        conditions.append(AuditLog.created_at >= from_date)
    if to_date:
        conditions.append(AuditLog.created_at <= to_date)

    total = await db.scalar(
        select(func.count(AuditLog.id)).where(and_(*conditions))
    ) or 0

    stmt = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(desc(AuditLog.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 1,
    }
