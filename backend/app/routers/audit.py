import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from app.dependencies import DB, CurrentTenant, CurrentUser, require_permission, get_tenant, get_current_user
from app.schemas.audit import AuditLogOut
from app.services import audit as audit_service

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/")
async def list_audit_logs(
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    actor_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    tenant=Depends(get_tenant),
    current_user=Depends(require_permission("audit_logs", "view")),
):
    """Query tenant-scoped audit trail with filtering and pagination."""
    result = await audit_service.get_audit_logs(
        db,
        tenant_id=str(tenant.id),
        page=page,
        limit=limit,
        actor_id=str(actor_id) if actor_id else None,
        action=action,
        entity_type=entity_type,
        from_date=from_date,
        to_date=to_date,
    )
    items_out = [
        AuditLogOut(
            id=item.id,
            tenant_id=item.tenant_id,
            actor_id=item.actor_id,
            action=item.action,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            ip_address=item.ip_address,
            metadata_=item.metadata_,
            created_at=item.created_at,
        )
        for item in result["items"]
    ]
    return {
        "success": True,
        "items": items_out,
        "total": result["total"],
        "page": result["page"],
        "limit": result["limit"],
        "pages": result["pages"],
    }
