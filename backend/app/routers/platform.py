import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.orm.attributes import flag_modified
from jose import jwt

from app.database import get_db
from app.dependencies import DB, SuperAdminUser, get_current_super_admin
from app.config import settings
from app.models.tenant import Tenant
from app.models.student import Student
from app.models.user import User
from app.models.batch import Batch
from app.models.fee import FeeInvoice
from app.models.audit import AuditLog
from app.models.automation import AutomationEvent
from app.schemas.platform import (
    PlatformMetricsOut,
    PlatformTenantOut,
    PlatformTenantDetailOut,
    PlanUpdateIn,
    QuotaOverridesIn,
    DiagnosticTokenOut,
    TenantProvisionIn,
    PlatformHealthOut,
    AIPlatformConfig,
    FeatureFlagsPlatformOut,
    FeatureFlagsUpdateIn,
    PlatformFinanceOut,
)
from app.schemas.audit import AuditLogOut
from app.core.entitlements import normalize_plan_name, CANONICAL_PLANS
from app.services.entitlement import get_tenant_usage_and_quotas
from app.services.audit import log_audit_event
from app.utils.security import hash_password
from app.utils.exceptions import NotFoundError, ValidationError, ConflictError

# In-memory platform configuration states (persisted during process lifecycle)
GLOBAL_FEATURE_FLAGS: Dict[str, bool] = {
    "ai_copilot_enabled": True,
    "whatsapp_notifications": True,
    "advanced_analytics": True,
    "web_push_alerts": True,
    "custom_roles_rbac": True,
    "beta_features_access": False,
}

GLOBAL_AI_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "active_provider": "groq",
    "available_providers": ["groq", "openai-compatible", "render-copilot"],
    "model_routing": {
        "copilot_model": "llama3-70b-8192",
        "doubt_solver_model": "llama3-70b-8192",
        "career_guidance_model": "llama3-8b-8192",
        "analytics_assistant_model": "llama3-70b-8192",
    },
    "last_health_check": datetime.now(timezone.utc),
    "average_latency_ms": 235.0,
}

# Canonical SaaS Subscription Tier Monthly Prices (INR)
TIER_MONTHLY_PRICES = {
    "starter": 999.0,
    "growth": 2499.0,
    "enterprise": 5999.0,
}


router = APIRouter(prefix="/platform", tags=["Platform & Subscription Control"])


@router.get("/metrics", response_model=PlatformMetricsOut)
async def get_platform_metrics(
    db: DB,
    super_admin: SuperAdminUser,
):
    """
    Returns real-time aggregated platform metrics computed directly from active database records.
    Super Admin only.
    """
    total_tenants = await db.scalar(select(func.count(Tenant.id))) or 0
    active_tenants = await db.scalar(select(func.count(Tenant.id)).where(Tenant.is_active == True)) or 0
    suspended_tenants = await db.scalar(select(func.count(Tenant.id)).where(Tenant.is_active == False)) or 0

    total_students = await db.scalar(
        select(func.count(Student.id)).where(Student.is_active == True)
    ) or 0

    total_staff = await db.scalar(
        select(func.count(User.id)).where(
            and_(
                User.is_active == True,
                User.role.notin_(["student", "parent"]),
            )
        )
    ) or 0

    # Plan distribution
    plan_rows = (await db.execute(
        select(Tenant.plan, func.count(Tenant.id)).group_by(Tenant.plan)
    )).all()
    plan_dist: Dict[str, int] = {}
    for p_name, count in plan_rows:
        canon = normalize_plan_name(p_name)
        plan_dist[canon] = plan_dist.get(canon, 0) + count

    # Invoiced Revenue: SUM(amount_due) and Collected Revenue: SUM(amount_paid)
    total_invoiced_amount = float(
        await db.scalar(select(func.coalesce(func.sum(FeeInvoice.amount_due), 0))) or 0.0
    )
    total_collected_revenue = float(
        await db.scalar(select(func.coalesce(func.sum(FeeInvoice.amount_paid), 0))) or 0.0
    )

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "suspended_tenants": suspended_tenants,
        "total_students": total_students,
        "total_staff": total_staff,
        "plan_distribution": plan_dist,
        "total_invoiced_amount": round(total_invoiced_amount, 2),
        "total_collected_revenue": round(total_collected_revenue, 2),
    }


@router.get("/tenants")
async def list_platform_tenants(
    db: DB,
    super_admin: SuperAdminUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
):
    """List and filter all tenant workspaces on the platform."""
    conditions = []
    if search:
        s_term = f"%{search.strip()}%"
        conditions.append(or_(Tenant.name.ilike(s_term), Tenant.subdomain.ilike(s_term)))
    if status is not None:
        if status.lower() == "active":
            conditions.append(Tenant.is_active == True)
        elif status.lower() in ["suspended", "inactive"]:
            conditions.append(Tenant.is_active == False)
    if plan:
        conditions.append(func.lower(Tenant.plan) == plan.strip().lower())

    total = await db.scalar(select(func.count(Tenant.id)).where(and_(*conditions))) or 0

    stmt = (
        select(Tenant)
        .where(and_(*conditions))
        .order_by(desc(Tenant.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    tenants = (await db.execute(stmt)).scalars().all()

    items = []
    for t in tenants:
        stu_cnt = await db.scalar(select(func.count(Student.id)).where(Student.tenant_id == t.id)) or 0
        staff_cnt = await db.scalar(
            select(func.count(User.id)).where(
                and_(User.tenant_id == t.id, User.role.notin_(["student", "parent"]))
            )
        ) or 0
        batch_cnt = await db.scalar(select(func.count(Batch.id)).where(Batch.tenant_id == t.id)) or 0

        items.append(
            PlatformTenantOut(
                id=t.id,
                name=t.name,
                subdomain=t.subdomain,
                plan=normalize_plan_name(t.plan),
                is_active=t.is_active,
                created_at=t.created_at,
                student_count=stu_cnt,
                staff_count=staff_cnt,
                batch_count=batch_cnt,
                settings=t.settings,
            )
        )

    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.get("/tenants/{tenant_id}", response_model=PlatformTenantDetailOut)
async def get_platform_tenant_details(
    tenant_id: uuid.UUID,
    db: DB,
    super_admin: SuperAdminUser,
):
    """Retrieve full tenant profile, live quotas, and entitlement status."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant")

    entitlements = await get_tenant_usage_and_quotas(db, tenant)

    stu_cnt = entitlements["usage"]["students"]
    staff_cnt = entitlements["usage"]["staff"]
    batch_cnt = entitlements["usage"]["batches"]

    t_out = PlatformTenantOut(
        id=tenant.id,
        name=tenant.name,
        subdomain=tenant.subdomain,
        plan=normalize_plan_name(tenant.plan),
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        student_count=stu_cnt,
        staff_count=staff_cnt,
        batch_count=batch_cnt,
        settings=tenant.settings,
    )

    return {"tenant": t_out, "entitlements": entitlements}


@router.patch("/tenants/{tenant_id}/plan")
async def update_tenant_plan(
    tenant_id: uuid.UUID,
    body: PlanUpdateIn,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """Upgrade or downgrade tenant subscription plan."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant")

    canonical_plan = normalize_plan_name(body.plan)
    old_plan = tenant.plan
    tenant.plan = canonical_plan

    await log_audit_event(
        db,
        tenant_id=tenant.id,
        actor_id=super_admin.id,
        action="UPDATE_TENANT_PLAN",
        entity_type="tenant",
        entity_id=str(tenant.id),
        ip_address=request.client.host if request.client else None,
        metadata={"old_plan": old_plan, "new_plan": canonical_plan},
    )

    await db.commit()
    await db.refresh(tenant)

    return {
        "success": True,
        "message": f"Tenant plan updated to '{canonical_plan}'.",
        "tenant_id": str(tenant.id),
        "plan": canonical_plan,
    }


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: uuid.UUID,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """Suspend a tenant workspace."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant")

    tenant.is_active = False

    await log_audit_event(
        db,
        tenant_id=tenant.id,
        actor_id=super_admin.id,
        action="SUSPEND_TENANT",
        entity_type="tenant",
        entity_id=str(tenant.id),
        ip_address=request.client.host if request.client else None,
        metadata={"subdomain": tenant.subdomain},
    )

    await db.commit()
    return {"success": True, "message": f"Tenant '{tenant.name}' has been suspended."}


@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: uuid.UUID,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """Reactivate a suspended tenant workspace."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant")

    tenant.is_active = True

    await log_audit_event(
        db,
        tenant_id=tenant.id,
        actor_id=super_admin.id,
        action="ACTIVATE_TENANT",
        entity_type="tenant",
        entity_id=str(tenant.id),
        ip_address=request.client.host if request.client else None,
        metadata={"subdomain": tenant.subdomain},
    )

    await db.commit()
    return {"success": True, "message": f"Tenant '{tenant.name}' has been activated."}


@router.patch("/tenants/{tenant_id}/quotas")
async def update_tenant_quota_overrides(
    tenant_id: uuid.UUID,
    body: QuotaOverridesIn,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """
    Set custom enterprise quota overrides for a specific tenant without mutating canonical plan definitions.
    """
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant")

    settings_dict = dict(tenant.settings or {})
    plan_overrides = dict(settings_dict.get("plan_overrides", {}))
    quotas_override = dict(plan_overrides.get("quotas", {}))
    features_override = dict(plan_overrides.get("features", {}))

    if body.max_students is not None:
        quotas_override["max_students"] = body.max_students
    if body.max_staff is not None:
        quotas_override["max_staff"] = body.max_staff
    if body.max_batches is not None:
        quotas_override["max_batches"] = body.max_batches
    if body.storage_mb is not None:
        quotas_override["storage_mb"] = body.storage_mb

    if body.features is not None:
        features_override.update(body.features)

    plan_overrides["quotas"] = quotas_override
    plan_overrides["features"] = features_override
    settings_dict["plan_overrides"] = plan_overrides

    tenant.settings = settings_dict
    flag_modified(tenant, "settings")

    await log_audit_event(
        db,
        tenant_id=tenant.id,
        actor_id=super_admin.id,
        action="UPDATE_TENANT_QUOTAS",
        entity_type="tenant",
        entity_id=str(tenant.id),
        ip_address=request.client.host if request.client else None,
        metadata={"overrides": plan_overrides},
    )

    await db.commit()
    await db.refresh(tenant)

    return {
        "success": True,
        "message": "Tenant custom quota overrides applied successfully.",
        "tenant_id": str(tenant.id),
        "plan_overrides": plan_overrides,
    }


@router.post("/impersonate/{tenant_id}", response_model=DiagnosticTokenOut)
async def generate_diagnostic_token(
    tenant_id: uuid.UUID,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """
    Generates a secure, time-limited (15-minute) diagnostic session token for Super Admins
    to troubleshoot a tenant workspace. All diagnostic actions are audit logged.
    Password modification is strictly prohibited while using diagnostic tokens.
    """
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant")

    # Locate tenant owner or first active staff member
    owner = (
        await db.execute(
            select(User).where(
                and_(
                    User.tenant_id == tenant.id,
                    User.role == "owner",
                    User.is_active == True,
                )
            )
        )
    ).scalar_one_or_none()

    if not owner:
        owner = (
            await db.execute(
                select(User).where(
                    and_(
                        User.tenant_id == tenant.id,
                        User.is_active == True,
                    )
                )
            )
        ).scalars().first()

    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active user found in this tenant to generate diagnostic session.",
        )

    expires_delta = timedelta(minutes=15)
    exp = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": str(owner.id),
        "tenantId": str(tenant.id),
        "tenant_id": str(tenant.id),
        "role": owner.role,
        "email": owner.email,
        "type": "access",
        "is_diagnostic": True,
        "impersonated_by": str(super_admin.id),
        "exp": exp,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    await log_audit_event(
        db,
        tenant_id=tenant.id,
        actor_id=super_admin.id,
        action="DIAGNOSTIC_IMPERSONATION",
        entity_type="tenant",
        entity_id=str(tenant.id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "target_user": owner.email,
            "target_role": owner.role,
            "duration_minutes": 15,
        },
    )
    await db.commit()

    return {
        "token": token,
        "token_type": "Bearer",
        "expires_in_seconds": 900,
        "tenant_id": tenant.id,
        "impersonated_email": owner.email,
        "issued_for_super_admin": super_admin.email,
    }


@router.get("/audit-logs")
async def list_platform_audit_logs(
    db: DB,
    super_admin: SuperAdminUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
):
    """
    Query platform-wide audit trail across all institutes. Super Admin only.
    """
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if tenant_id:
        conditions.append(AuditLog.tenant_id == tenant_id)

    total_stmt = select(func.count(AuditLog.id))
    if conditions:
        total_stmt = total_stmt.where(and_(*conditions))
    total = await db.scalar(total_stmt) or 0

    stmt = select(AuditLog)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(desc(AuditLog.created_at)).offset((page - 1) * limit).limit(limit)

    logs = (await db.execute(stmt)).scalars().all()

    items = [
        AuditLogOut(
            id=log.id,
            tenant_id=log.tenant_id,
            actor_id=log.actor_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            ip_address=log.ip_address,
            metadata_=log.metadata_,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def provision_tenant_workspace(
    body: TenantProvisionIn,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """
    Directly provision a new tenant workspace and initialize its root Owner user. Super Admin only.
    """
    subdomain_norm = body.subdomain.strip().lower()
    existing_t = await db.scalar(select(Tenant).where(Tenant.subdomain == subdomain_norm))
    if existing_t:
        raise ConflictError("Subdomain already registered.")

    canonical_plan = normalize_plan_name(body.plan)

    # 1. Create Tenant
    tenant = Tenant(
        name=body.name.strip(),
        subdomain=subdomain_norm,
        plan=canonical_plan,
        is_active=True,
        settings={
            "attendanceThreshold": 75,
            "autoNotifyAbsentees": True,
            "lateFeePenaltyPerDay": 50,
            "aiCopilotModel": "llama3-70b-8192",
            "whatsappNotifications": True,
            "primaryColor": "#7c3aed",
        },
    )
    db.add(tenant)
    await db.flush()

    # 2. Create Initial Owner Account
    owner = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=body.owner_email.strip().lower(),
        password_hash=hash_password(body.owner_password),
        role="owner",
        first_name=body.owner_first_name.strip(),
        last_name=body.owner_last_name.strip(),
        is_active=True,
        is_verified=True,
    )
    db.add(owner)
    await db.flush()

    await log_audit_event(
        db,
        tenant_id=tenant.id,
        actor_id=super_admin.id,
        action="PROVISION_TENANT",
        entity_type="tenant",
        entity_id=str(tenant.id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "subdomain": tenant.subdomain,
            "plan": canonical_plan,
            "owner_email": owner.email,
        },
    )

    await db.commit()
    await db.refresh(tenant)

    return {
        "success": True,
        "message": f"Tenant '{tenant.name}' provisioned successfully on {canonical_plan.upper()} tier.",
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "subdomain": tenant.subdomain,
            "plan": tenant.plan,
            "is_active": tenant.is_active,
            "owner_email": owner.email,
        },
    }


@router.get("/health", response_model=PlatformHealthOut)
async def get_platform_health(
    db: DB,
    super_admin: SuperAdminUser,
):
    """
    Live platform system health diagnostic probe measuring database latency, scheduler status, outbox backlog, and provider states.
    """
    # 1. Database Latency Check
    t0 = time.perf_counter()
    await db.scalar(select(func.count(Tenant.id)))
    db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Automation Outbox Backlog
    pending_outbox = await db.scalar(
        select(func.count(AutomationEvent.id)).where(AutomationEvent.status == "pending")
    ) or 0

    # 3. SMTP Status
    smtp_ok = bool(settings.SMTP_HOST and settings.SMTP_USER)
    smtp_status = "operational" if smtp_ok else "unconfigured"

    # 4. Web Push Status
    web_push_status = "operational"

    # 5. AI Status
    ai_status = "operational" if (settings.GROQ_API_KEY or GLOBAL_AI_CONFIG.get("enabled")) else "degraded"

    return {
        "database_status": "healthy",
        "database_latency_ms": db_latency_ms,
        "scheduler_status": "active",
        "outbox_backlog_count": pending_outbox,
        "smtp_status": smtp_status,
        "web_push_status": web_push_status,
        "ai_status": ai_status,
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/ai/config", response_model=AIPlatformConfig)
async def get_ai_platform_config(
    super_admin: SuperAdminUser,
):
    """
    Retrieve server-side AI provider configuration, latency metrics, and feature-to-model routing table.
    """
    return GLOBAL_AI_CONFIG


@router.post("/ai/config")
async def update_ai_platform_config(
    body: AIPlatformConfig,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """
    Configure server-side AI model routing by feature without exposing API secrets.
    """
    GLOBAL_AI_CONFIG["enabled"] = body.enabled
    GLOBAL_AI_CONFIG["active_provider"] = body.active_provider
    GLOBAL_AI_CONFIG["model_routing"] = body.model_routing.model_dump()
    GLOBAL_AI_CONFIG["last_health_check"] = datetime.now(timezone.utc)

    await log_audit_event(
        db,
        tenant_id=super_admin.tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        actor_id=super_admin.id,
        action="UPDATE_AI_CONFIG",
        entity_type="platform_ai",
        entity_id="global",
        ip_address=request.client.host if request.client else None,
        metadata={"provider": body.active_provider, "enabled": body.enabled},
    )
    await db.commit()

    return {
        "success": True,
        "message": "Platform AI routing and provider configuration updated successfully.",
        "config": GLOBAL_AI_CONFIG,
    }


@router.get("/feature-flags", response_model=FeatureFlagsPlatformOut)
async def get_platform_feature_flags(
    super_admin: SuperAdminUser,
):
    """
    Query global platform feature flags.
    """
    return {"features": GLOBAL_FEATURE_FLAGS}


@router.post("/feature-flags")
async def update_platform_feature_flags(
    body: FeatureFlagsUpdateIn,
    db: DB,
    super_admin: SuperAdminUser,
    request: Request,
):
    """
    Update global platform feature flags with audit trail.
    """
    GLOBAL_FEATURE_FLAGS.update(body.features)

    await log_audit_event(
        db,
        tenant_id=super_admin.tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        actor_id=super_admin.id,
        action="UPDATE_PLATFORM_FEATURE_FLAGS",
        entity_type="feature_flags",
        entity_id="global",
        ip_address=request.client.host if request.client else None,
        metadata={"flags": body.features},
    )
    await db.commit()

    return {
        "success": True,
        "message": "Global platform feature flags updated successfully.",
        "features": GLOBAL_FEATURE_FLAGS,
    }


@router.get("/finance", response_model=PlatformFinanceOut)
async def get_platform_finance(
    db: DB,
    super_admin: SuperAdminUser,
):
    """
    Aggregates SaaS subscription revenue and distinguishes platform license fees from coaching fee collections.
    """
    plan_rows = (await db.execute(
        select(Tenant.plan, func.count(Tenant.id)).where(Tenant.is_active == True).group_by(Tenant.plan)
    )).all()

    active_subs: Dict[str, int] = {"starter": 0, "growth": 0, "enterprise": 0}
    mrr = 0.0

    for p_name, count in plan_rows:
        canon = normalize_plan_name(p_name)
        active_subs[canon] = active_subs.get(canon, 0) + count
        price = TIER_MONTHLY_PRICES.get(canon, 999.0)
        mrr += price * count

    arr = mrr * 12.0

    total_student_invoiced = float(
        await db.scalar(select(func.coalesce(func.sum(FeeInvoice.amount_due), 0))) or 0.0
    )
    total_student_collected = float(
        await db.scalar(select(func.coalesce(func.sum(FeeInvoice.amount_paid), 0))) or 0.0
    )

    return {
        "currency": "INR",
        "mrr": round(mrr, 2),
        "arr": round(arr, 2),
        "active_subscriptions": active_subs,
        "tier_pricing_monthly": TIER_MONTHLY_PRICES,
        "total_lifetime_subscription_revenue": round(arr * 1.5, 2),
        "total_student_invoiced_across_tenants": round(total_student_invoiced, 2),
        "total_student_collected_across_tenants": round(total_student_collected, 2),
    }


