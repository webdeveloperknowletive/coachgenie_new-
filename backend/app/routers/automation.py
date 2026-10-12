import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.dependencies import get_tenant, require_roles, DB
from app.models.automation import AutomationRule, AutomationExecution, WebPushSubscription
from app.models.user import User
from app.schemas.automation import (
    AutomationRuleCreate,
    AutomationRuleOut,
    LateFeeWaiverRequest,
    WebPushSubscribeRequest,
)
from app.services import automation_engine
from app.services.entitlement import EntitlementService

router = APIRouter(prefix="/automation", tags=["Automation"])


@router.get("/rules", response_model=List[AutomationRuleOut])
async def list_rules(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin", "counselor")),
):
    """
    Returns configured automation policies for the tenant.
    """
    rules = await automation_engine.get_tenant_rules(db, str(tenant.id))
    return rules


@router.put("/rules/{rule_type}", response_model=AutomationRuleOut)
async def update_rule(
    rule_type: str,
    body: AutomationRuleCreate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    """
    Configures an automation rule (e.g. attendance_alert, fee_overdue) with server-side validation.
    """
    # Gated feature verification if advanced
    if rule_type == "late_fee":
        await EntitlementService.check_feature(tenant, "custom_automation")

    rule = await automation_engine.upsert_tenant_rule(
        db, str(tenant.id), rule_type, body.config, user_id=current_user.id
    )
    return rule


@router.post("/trigger-eval")
async def trigger_eval(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    """
    Manually triggers safe, idempotent evaluation of tenant automation policies.
    """
    att_count = await automation_engine.evaluate_attendance_automation(db, str(tenant.id))
    fee_count = await automation_engine.evaluate_fee_overdue_automation(db, str(tenant.id))

    return {
        "success": True,
        "message": f"Automation evaluated: {att_count} attendance alerts, {fee_count} fee actions",
        "data": {"attendance_alerts": att_count, "fee_actions": fee_count},
    }


@router.post("/late-fees/waive")
async def waive_fee(
    body: LateFeeWaiverRequest,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    """
    Administratively waives or reverses an overdue fee penalty with audit logging.
    """
    inst = await automation_engine.waive_late_fee(
        db, str(tenant.id), body.installment_id, body.waiver_amount, body.reason, current_user
    )
    return {
        "success": True,
        "message": f"Waiver of ₹{body.waiver_amount} applied to installment #{inst.installment_no}",
        "data": {
            "installment_id": str(inst.id),
            "amount_due": float(inst.amount_due),
            "amount_paid": float(inst.amount_paid),
        },
    }


@router.get("/logs")
async def get_logs(
    db: DB,
    limit: int = Query(50, ge=1, le=200),
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    """
    Returns recent automation execution and idempotency records.
    """
    stmt = (
        select(AutomationExecution)
        .where(AutomationExecution.tenant_id == tenant.id)
        .order_by(AutomationExecution.executed_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    executions = list(res.scalars().all())

    return {
        "success": True,
        "data": [
            {
                "id": str(e.id),
                "rule_type": e.rule_type,
                "idempotency_key": e.idempotency_key,
                "entity_id": str(e.entity_id),
                "status": e.status,
                "details": e.details,
                "executed_at": str(e.executed_at),
            }
            for e in executions
        ],
    }


# Web Push Subscriptions router extension
push_router = APIRouter(prefix="/notifications/push", tags=["WebPush"])


@push_router.post("/subscribe")
async def subscribe_web_push(
    body: WebPushSubscribeRequest,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("student", "parent", "tutor", "counselor", "owner", "admin")),
):
    """
    Registers a browser Web Push subscription for the authenticated user.
    """
    # Delete old subscription for same endpoint if exists
    await db.execute(
        delete(WebPushSubscription).where(
            and_(
                WebPushSubscription.tenant_id == tenant.id,
                WebPushSubscription.user_id == current_user.id,
                WebPushSubscription.endpoint == body.endpoint,
            )
        )
    )
    sub = WebPushSubscription(
        tenant_id=tenant.id,
        user_id=current_user.id,
        endpoint=body.endpoint,
        p256dh_key=body.p256dh_key,
        auth_key=body.auth_key,
    )
    db.add(sub)
    await db.flush()
    return {"success": True, "message": "Subscribed to browser notifications"}


@push_router.delete("/unsubscribe")
async def unsubscribe_web_push(
    endpoint: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("student", "parent", "tutor", "counselor", "owner", "admin")),
):
    """
    Unsubscribes a browser Web Push subscription.
    """
    await db.execute(
        delete(WebPushSubscription).where(
            and_(
                WebPushSubscription.tenant_id == tenant.id,
                WebPushSubscription.user_id == current_user.id,
                WebPushSubscription.endpoint == endpoint,
            )
        )
    )
    await db.flush()
    return {"success": True, "message": "Unsubscribed from browser notifications"}
