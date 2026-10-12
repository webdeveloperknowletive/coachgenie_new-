import logging
import uuid
from typing import List, Dict, Set, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.role import CustomRole
from app.services.audit import log_audit_event
from app.utils.exceptions import NotFoundError, ConflictError

logger = logging.getLogger("coaching_erp")

# Predefined permission mappings for legacy built-in roles
LEGACY_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "owner": {"*.*"},
    "super_admin": {"*.*"},
    "admin": {
        "leads.*",
        "admissions.*",
        "students.*",
        "batches.*",
        "attendance.*",
        "fees.*",
        "exams.*",
        "growth_cards.*",
        "syllabus.*",
        "notifications.*",
        "reports.*",
        "settings.view",
        "settings.edit",
        "roles.*",
        "audit_logs.view",
    },
    "counselor": {
        "leads.*",
        "admissions.*",
        "students.view",
        "students.create",
        "students.edit",
        "batches.view",
        "fees.view",
        "fees.create",
        "notifications.view",
    },
    "tutor": {
        "batches.view",
        "students.view",
        "classes.*",
        "attendance.*",
        "exams.*",
        "growth_cards.*",
        "syllabus.*",
        "notifications.view",
    },
    "student": {
        "students.view",
        "batches.view",
        "attendance.view",
        "exams.view",
        "fees.view",
        "growth_cards.view",
        "syllabus.view",
    },
    "parent": {
        "students.view",
        "attendance.view",
        "exams.view",
        "fees.view",
        "growth_cards.view",
    },
}


def permission_matches(user_perms: Set[str], resource: str, action: str) -> bool:
    """Check if a set of granted permissions satisfies resource.action."""
    target_exact = f"{resource.lower()}.{action.lower()}"
    target_resource_wildcard = f"{resource.lower()}.*"
    global_wildcard = "*.*"

    return (
        global_wildcard in user_perms
        or target_resource_wildcard in user_perms
        or target_exact in user_perms
    )


def has_permission(user: User, resource: str, action: str) -> bool:
    """
    Centralized server-side permission evaluator.
    Evaluates legacy built-in roles and dynamic custom roles attached to the user.
    """
    if not user or not user.is_active:
        return False

    role_key = (user.role or "").strip().lower()

    # 1. Super Admin & Institute Owner have full system access
    if role_key in {"owner", "super_admin"}:
        return True

    # 2. Check dynamic CustomRole assigned to the user
    if getattr(user, "custom_role", None) and user.custom_role and user.custom_role.is_active:
        custom_perms = set(user.custom_role.permissions or [])
        if permission_matches(custom_perms, resource, action):
            return True

    # 3. Check legacy built-in role permissions
    if role_key in LEGACY_ROLE_PERMISSIONS:
        builtin_perms = LEGACY_ROLE_PERMISSIONS[role_key]
        if permission_matches(builtin_perms, resource, action):
            return True

    return False


# ── Custom Role Management CRUD ───────────────────────────────────────────────

async def get_custom_roles(db: AsyncSession, tenant_id: str | uuid.UUID) -> List[CustomRole]:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    stmt = (
        select(CustomRole)
        .where(CustomRole.tenant_id == t_uuid)
        .order_by(CustomRole.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_custom_role(
    db: AsyncSession, tenant_id: str | uuid.UUID, role_id: str | uuid.UUID
) -> CustomRole:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    r_uuid = uuid.UUID(str(role_id)) if isinstance(role_id, (str, uuid.UUID)) else role_id

    stmt = select(CustomRole).where(
        and_(CustomRole.tenant_id == t_uuid, CustomRole.id == r_uuid)
    )
    role = (await db.execute(stmt)).scalar_one_or_none()
    if not role:
        raise NotFoundError("Custom Role")
    return role


async def create_custom_role(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    data: dict,
    actor_id: str | uuid.UUID | None = None,
    ip_address: str | None = None,
) -> CustomRole:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    name_clean = data["name"].strip()

    # Unique check
    existing = await db.scalar(
        select(CustomRole.id).where(
            and_(
                CustomRole.tenant_id == t_uuid,
                func.lower(CustomRole.name) == name_clean.lower(),
            )
        )
    )
    if existing:
        raise ConflictError(f"A role named '{name_clean}' already exists in this institute.")

    role = CustomRole(
        id=uuid.uuid4(),
        tenant_id=t_uuid,
        name=name_clean,
        description=data.get("description"),
        permissions=data.get("permissions", []),
        is_active=True,
    )
    db.add(role)
    await db.flush()

    # Audit log
    await log_audit_event(
        db,
        tenant_id=t_uuid,
        actor_id=actor_id,
        action="CREATE_ROLE",
        entity_type="custom_role",
        entity_id=str(role.id),
        ip_address=ip_address,
        metadata={"name": role.name, "permissions": role.permissions},
    )

    await db.commit()
    await db.refresh(role)
    return role


async def update_custom_role(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    role_id: str | uuid.UUID,
    data: dict,
    actor_id: str | uuid.UUID | None = None,
    ip_address: str | None = None,
) -> CustomRole:
    role = await get_custom_role(db, tenant_id, role_id)
    t_uuid = role.tenant_id

    if "name" in data and data["name"]:
        name_clean = data["name"].strip()
        if name_clean.lower() != role.name.lower():
            dup = await db.scalar(
                select(CustomRole.id).where(
                    and_(
                        CustomRole.tenant_id == t_uuid,
                        func.lower(CustomRole.name) == name_clean.lower(),
                        CustomRole.id != role.id,
                    )
                )
            )
            if dup:
                raise ConflictError(f"A role named '{name_clean}' already exists.")
            role.name = name_clean

    if "description" in data:
        role.description = data["description"]
    if "permissions" in data and data["permissions"] is not None:
        role.permissions = data["permissions"]
    if "is_active" in data and data["is_active"] is not None:
        role.is_active = data["is_active"]

    await db.flush()

    # Audit log
    await log_audit_event(
        db,
        tenant_id=t_uuid,
        actor_id=actor_id,
        action="UPDATE_ROLE",
        entity_type="custom_role",
        entity_id=str(role.id),
        ip_address=ip_address,
        metadata={"name": role.name, "permissions": role.permissions, "is_active": role.is_active},
    )

    await db.commit()
    await db.refresh(role)
    return role


async def delete_custom_role(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    role_id: str | uuid.UUID,
    actor_id: str | uuid.UUID | None = None,
    ip_address: str | None = None,
) -> dict:
    role = await get_custom_role(db, tenant_id, role_id)
    t_uuid = role.tenant_id

    # Check if active users are assigned to this custom role
    assigned_count = await db.scalar(
        select(func.count(User.id)).where(
            and_(User.tenant_id == t_uuid, User.custom_role_id == role.id)
        )
    ) or 0

    if assigned_count > 0:
        raise ConflictError(
            f"Cannot delete role '{role.name}' because {assigned_count} user(s) are currently assigned to it. Please reassign them first."
        )

    await db.delete(role)
    await db.flush()

    # Audit log
    await log_audit_event(
        db,
        tenant_id=t_uuid,
        actor_id=actor_id,
        action="DELETE_ROLE",
        entity_type="custom_role",
        entity_id=str(role_id),
        ip_address=ip_address,
        metadata={"name": role.name},
    )

    await db.commit()
    return {"success": True, "message": f"Role '{role.name}' deleted successfully."}
