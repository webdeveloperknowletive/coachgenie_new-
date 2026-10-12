import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


# Canonical actions
VALID_ACTIONS = {
    "view",
    "create",
    "edit",
    "delete",
    "approve",
    "publish",
    "export",
    "assign",
    "manage",
    "*",
}

# Canonical resources
VALID_RESOURCES = {
    "leads",
    "admissions",
    "students",
    "batches",
    "attendance",
    "fees",
    "exams",
    "growth_cards",
    "syllabus",
    "notifications",
    "reports",
    "settings",
    "audit_logs",
    "roles",
    "*",
}


def validate_permission_string(perm: str) -> str:
    perm = perm.strip().lower()
    if perm == "*.*" or perm == "*":
        return "*.*"
    if "." not in perm:
        raise ValueError(f"Invalid permission format '{perm}'. Must be '<resource>.<action>'")
    resource, action = perm.split(".", 1)
    if resource not in VALID_RESOURCES:
        raise ValueError(f"Invalid resource '{resource}'. Allowed: {sorted(list(VALID_RESOURCES))}")
    if action not in VALID_ACTIONS:
        raise ValueError(f"Invalid action '{action}'. Allowed: {sorted(list(VALID_ACTIONS))}")
    return f"{resource}.{action}"


class CustomRoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

    @field_validator("permissions")
    @classmethod
    def validate_perms(cls, v: List[str]) -> List[str]:
        cleaned = []
        for p in v:
            cleaned.append(validate_permission_string(p))
        return list(set(cleaned))


class CustomRoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("permissions")
    @classmethod
    def validate_perms(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        cleaned = []
        for p in v:
            cleaned.append(validate_permission_string(p))
        return list(set(cleaned))


class CustomRoleOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str] = None
    permissions: List[str]
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AvailablePermissionsOut(BaseModel):
    resources: List[str]
    actions: List[str]
    common_templates: dict
