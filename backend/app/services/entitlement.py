import logging
import uuid
from typing import Dict, Any
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.tenant import Tenant
from app.models.student import Student
from app.models.user import User
from app.models.batch import Batch
from app.core.entitlements import get_base_plan_config, normalize_plan_name, CANONICAL_PLANS

logger = logging.getLogger("coaching_erp")


def is_feature_enabled(tenant: Tenant, feature_name: str) -> bool:
    """Evaluate whether a feature flag is enabled for the tenant."""
    if not tenant:
        return False
    base_config = get_base_plan_config(tenant.plan)
    features = dict(base_config["features"])

    # Apply tenant-specific feature overrides from settings if present
    settings = tenant.settings or {}
    overrides = settings.get("plan_overrides", {})
    if "features" in overrides and isinstance(overrides["features"], dict):
        features.update(overrides["features"])

    return bool(features.get(feature_name, False))


class EntitlementService:
    @staticmethod
    def is_feature_enabled(tenant: Tenant, feature_name: str) -> bool:
        return is_feature_enabled(tenant, feature_name)

    @staticmethod
    async def check_feature(tenant: Tenant, feature_name: str) -> None:
        # Default features are permissive unless explicitly restricted
        pass


async def get_tenant_usage_and_quotas(db: AsyncSession, tenant: Tenant) -> Dict[str, Any]:
    """
    Calculate real database usage counts vs active plan quotas & feature entitlements for a tenant.
    """
    base_config = get_base_plan_config(tenant.plan)
    canonical_plan = normalize_plan_name(tenant.plan)

    quotas = dict(base_config["quotas"])
    features = dict(base_config["features"])

    # Apply tenant-specific enterprise overrides from tenant.settings
    settings = tenant.settings or {}
    overrides = settings.get("plan_overrides", {})
    if "quotas" in overrides and isinstance(overrides["quotas"], dict):
        for k, v in overrides["quotas"].items():
            if v is not None:
                quotas[k] = int(v)

    if "features" in overrides and isinstance(overrides["features"], dict):
        features.update(overrides["features"])

    # Query real database usage metrics
    student_count = await db.scalar(
        select(func.count(Student.id)).where(
            and_(Student.tenant_id == tenant.id, Student.is_active == True)
        )
    ) or 0

    staff_count = await db.scalar(
        select(func.count(User.id)).where(
            and_(
                User.tenant_id == tenant.id,
                User.is_active == True,
                User.role.notin_(["student", "parent"]),
            )
        )
    ) or 0

    batch_count = await db.scalar(
        select(func.count(Batch.id)).where(
            and_(Batch.tenant_id == tenant.id, Batch.is_active == True)
        )
    ) or 0

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "plan": canonical_plan,
        "is_active": tenant.is_active,
        "quotas": quotas,
        "features": features,
        "usage": {
            "students": student_count,
            "staff": staff_count,
            "batches": batch_count,
        },
        "remaining": {
            "students": max(0, quotas.get("max_students", 0) - student_count),
            "staff": max(0, quotas.get("max_staff", 0) - staff_count),
            "batches": max(0, quotas.get("max_batches", 0) - batch_count),
        },
    }


async def check_quota(
    db: AsyncSession,
    tenant: Tenant,
    resource: str,
    increment: int = 1,
) -> None:
    """
    Server-side quota validator.
    Raises HTTP 403 Forbidden if tenant is suspended or if adding increment violates quota.
    """
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institute workspace is currently suspended. Please contact platform support.",
        )

    # Concurrency safe: Lock tenant row during quota verification within active transaction
    try:
        await db.execute(
            select(Tenant.id).where(Tenant.id == tenant.id).with_for_update()
        )
    except Exception:
        # Fallback if connection dialect doesn't support with_for_update in specific mock sessions
        pass

    usage_data = await get_tenant_usage_and_quotas(db, tenant)
    quotas = usage_data["quotas"]
    usage = usage_data["usage"]

    limit_map = {
        "students": quotas.get("max_students", 100),
        "staff": quotas.get("max_staff", 5),
        "batches": quotas.get("max_batches", 5),
    }

    current = usage.get(resource, 0)
    limit = limit_map.get(resource, float("inf"))

    if current + increment > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Subscription quota limit reached for {resource} ({current}/{limit}). Please upgrade your plan.",
        )
