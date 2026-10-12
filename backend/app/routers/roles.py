import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, status, Query
from app.dependencies import DB, CurrentTenant, CurrentUser, require_permission, get_tenant, get_current_user
from app.schemas.role import (
    CustomRoleCreate,
    CustomRoleUpdate,
    CustomRoleOut,
    AvailablePermissionsOut,
    VALID_RESOURCES,
    VALID_ACTIONS,
)
from app.services import rbac as rbac_service

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


@router.get("/meta/permissions", response_model=AvailablePermissionsOut)
async def get_available_permissions(
    current_user=Depends(get_current_user),
):
    """Returns available resources, actions, and standard role templates for UI configuration."""
    common_templates = {
        "Accountant": ["fees.view", "fees.create", "fees.edit", "fees.export", "reports.view"],
        "Receptionist": ["leads.view", "leads.create", "leads.edit", "admissions.view", "admissions.create", "attendance.view"],
        "Senior Counselor": ["leads.*", "admissions.*", "students.view", "batches.view"],
        "Exam Coordinator": ["exams.*", "batches.view", "students.view", "reports.view"],
    }
    return {
        "resources": sorted(list(VALID_RESOURCES - {"*"})),
        "actions": sorted(list(VALID_ACTIONS - {"*"})),
        "common_templates": common_templates,
    }


@router.get("/", response_model=List[CustomRoleOut])
async def list_custom_roles(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_permission("roles", "view")),
):
    """List all custom roles defined for the current tenant."""
    roles = await rbac_service.get_custom_roles(db, str(tenant.id))
    return roles


@router.post("/", response_model=CustomRoleOut, status_code=status.HTTP_201_CREATED)
async def create_custom_role(
    request: Request,
    body: CustomRoleCreate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_permission("roles", "create")),
):
    """Create a new custom role for the current tenant."""
    ip_addr = request.client.host if request.client else None
    role = await rbac_service.create_custom_role(
        db,
        tenant_id=str(tenant.id),
        data=body.model_dump(),
        actor_id=str(current_user.id),
        ip_address=ip_addr,
    )
    return role


@router.get("/{role_id}", response_model=CustomRoleOut)
async def get_custom_role(
    role_id: uuid.UUID,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_permission("roles", "view")),
):
    """Get a specific custom role by ID."""
    role = await rbac_service.get_custom_role(db, str(tenant.id), str(role_id))
    return role


@router.patch("/{role_id}", response_model=CustomRoleOut)
async def update_custom_role(
    request: Request,
    role_id: uuid.UUID,
    body: CustomRoleUpdate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_permission("roles", "edit")),
):
    """Update a custom role's name, description, active status, or permissions."""
    ip_addr = request.client.host if request.client else None
    role = await rbac_service.update_custom_role(
        db,
        tenant_id=str(tenant.id),
        role_id=str(role_id),
        data=body.model_dump(exclude_unset=True),
        actor_id=str(current_user.id),
        ip_address=ip_addr,
    )
    return role


@router.delete("/{role_id}")
async def delete_custom_role(
    request: Request,
    role_id: uuid.UUID,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_permission("roles", "delete")),
):
    """Delete a custom role (prevents deletion if users are currently assigned)."""
    ip_addr = request.client.host if request.client else None
    result = await rbac_service.delete_custom_role(
        db,
        tenant_id=str(tenant.id),
        role_id=str(role_id),
        actor_id=str(current_user.id),
        ip_address=ip_addr,
    )
    return result
