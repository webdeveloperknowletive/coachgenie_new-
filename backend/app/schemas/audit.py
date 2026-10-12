import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class AuditLogOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    actor_id: Optional[uuid.UUID] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
