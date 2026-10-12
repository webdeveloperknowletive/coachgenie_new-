# from fastapi import APIRouter, Depends, Query
# from app.database import get_db
# from sqlalchemy import select
# from app.models.notification import NotificationLog
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.dependencies import get_tenant, require_roles, DB
# from app.schemas.notification import (
#     TemplateCreate, TemplateOut,
#     SendNotificationRequest, NotificationLogOut
# )
# from app.services import notification as notif_service
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.exc import IntegrityError
# import traceback


# router = APIRouter(prefix="/notifications", tags=["Notifications"])


# @router.post("/templates", status_code=201)
# async def create_template(
#     body: TemplateCreate,
#     db: DB,
#     tenant=Depends(get_tenant),
#     current_user=Depends(require_roles("owner", "admin")),
# ):
#     try:
#         data = body.model_dump()
#         template = await notif_service.create_template(db, str(tenant.id), data)
#         await db.commit()
#         return {"success": True, "data": TemplateOut.model_validate(template)}
#     except IntegrityError:
#         await db.rollback()
#         raise HTTPException(status_code=409, detail="A template with this name and channel already exists.")
#     except Exception as e:
#         await db.rollback()
#         traceback.print_exc()  # prints full error to terminal
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/templates")
# async def list_templates(
#     db: DB,
#     tenant=Depends(get_tenant),
#     current_user=Depends(require_roles("owner", "counselor", "admin")),
# ):
#     templates = await notif_service.get_templates(db, str(tenant.id))
#     return {"success": True, "data": [TemplateOut.model_validate(t) for t in templates]}


# @router.post("/templates", status_code=201)
# async def create_template(
#     body: TemplateCreate,
#     db: DB,
#     tenant=Depends(get_tenant),
#     current_user=Depends(require_roles("owner")),
# ):
#     data = body.model_dump()
#     template = await notif_service.create_template(db, str(tenant.id), data)
#     await db.commit()
#     return {"success": True, "data": TemplateOut.model_validate(template)}


# @router.post("/logs/{log_id}/retry")
# async def retry_notification(
#     log_id: str,
#     db: AsyncSession = Depends(get_db),
# ):
#     # Fetch the original log entry
#     result = await db.execute(
#         select(NotificationLog).where(NotificationLog.id == log_id)
#     )
#     log = result.scalar_one_or_none()

#     if not log:
#         raise HTTPException(status_code=404, detail="Notification log not found")

#     if log.status != "failed":
#         raise HTTPException(status_code=400, detail="Only failed notifications can be retried")

#     # Re-dispatch based on channel
#     try:
#         if log.channel == "email":
#             await send_email(to=log.recipient_ref, subject=log.subject, body=log.body)
#         elif log.channel == "sms":
#             await send_sms(to=log.recipient_ref, body=log.body)
#         elif log.channel == "whatsapp":
#             await send_whatsapp(to=log.recipient_ref, body=log.body)

#         # Update log status
#         log.status = "sent"
#         log.sent_at = datetime.utcnow()
#         await db.commit()

#     except Exception as e:
#         log.status = "failed"
#         await db.commit()
#         raise HTTPException(status_code=502, detail=f"Resend failed: {str(e)}")

#     return {"detail": "Notification resent successfully"}

# @router.post("/send")
# async def send_notifications(
#     body: SendNotificationRequest,
#     db: DB,
#     tenant=Depends(get_tenant),
#     current_user=Depends(require_roles("owner", "counselor")),
# ):
#     logs = await notif_service.send_notifications(
#         db, str(tenant.id), str(body.template_id),
#         [r.model_dump() for r in body.recipients],  # ← changed
#         body.variables
#     )
#     await db.commit()
#     return {
#         "success": True,
#         "data": [NotificationLogOut.model_validate(l) for l in logs],
#         "sent": sum(1 for l in logs if l.status == "sent"),
#         "failed": sum(1 for l in logs if l.status == "failed"),
#         "total": len(logs),
#     }
# @router.post("/trigger-jobs")
# async def trigger_jobs(
#     tenant=Depends(get_tenant),
#     current_user=Depends(require_roles("owner")),
# ):
#     from app.scheduler import notify_overdue_fees, notify_low_attendance
#     await notify_overdue_fees()
#     await notify_low_attendance()
#     return {"success": True, "message": "Jobs triggered"}

# @router.get("/logs")
# async def get_logs(
#     db: DB,
#     tenant=Depends(get_tenant),
#     current_user=Depends(require_roles("owner")),
# ):
#     logs = await notif_service.get_logs(db, str(tenant.id))
#     return {"success": True, "data": [NotificationLogOut.model_validate(l) for l in logs]}


from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import traceback

from app.database import get_db
from app.models.notification import NotificationLog
from app.dependencies import get_tenant, require_roles, DB
from app.schemas.notification import (
    TemplateCreate, TemplateOut,
    SendNotificationRequest, NotificationLogOut
)
from app.services import notification as notif_service


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/templates", status_code=201)
async def create_template(
    body: TemplateCreate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    try:
        data = body.model_dump()
        template = await notif_service.create_template(db, str(tenant.id), data)
        # db.commit() removed — get_db() handles commit.
        return {"success": True, "data": TemplateOut.model_validate(template)}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A template with this name and channel already exists.")
    except Exception as e:
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_templates(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor", "admin")),
):
    templates = await notif_service.get_templates(db, str(tenant.id))
    return {"success": True, "data": [TemplateOut.model_validate(t) for t in templates]}


@router.post("/logs/{log_id}/retry")
async def retry_notification(
    log_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    result = await db.execute(
        select(NotificationLog).where(
            NotificationLog.id == log_id,
            NotificationLog.tenant_id == str(tenant.id),
        )
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="Notification log not found")

    if log.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed notifications can be retried")

    try:
        # Re-dispatch by delegating back to notif_service so all your
        # provider logic (Twilio, SendGrid, etc.) lives in one place.
        await notif_service.dispatch(
            channel=log.channel,
            recipient_ref=log.recipient_ref,
            subject=log.subject,
            body=log.body,
        )
        log.status = "sent"
        log.sent_at = datetime.utcnow()
        await db.flush()  # get_db() commits on clean exit.

    except Exception:
        log.status = "failed"
        await db.flush()
        traceback.print_exc()
        raise HTTPException(status_code=502, detail="Failed to resend notification.")

    return {"success": True, "detail": "Notification resent successfully"}


@router.post("/send")
async def send_notifications(
    body: SendNotificationRequest,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    logs = await notif_service.send_notifications(
        db, str(tenant.id), str(body.template_id),
        [r.model_dump() for r in body.recipients],
        body.variables,
    )
    # db.commit() removed — get_db() handles commit.
    return {
        "success": True,
        "data": [NotificationLogOut.model_validate(l) for l in logs],
        "sent":   sum(1 for l in logs if l.status == "sent"),
        "failed": sum(1 for l in logs if l.status == "failed"),
        "total":  len(logs),
    }


@router.post("/trigger-jobs")
async def trigger_jobs(
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner")),
):
    from app.scheduler import notify_overdue_fees, notify_low_attendance
    await notify_overdue_fees()
    await notify_low_attendance()
    return {"success": True, "message": "Jobs triggered"}


@router.get("/logs")
async def get_logs(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner")),
):
    logs = await notif_service.get_logs(db, str(tenant.id))
    return {"success": True, "data": [NotificationLogOut.model_validate(l) for l in logs]}


@router.get("/inbox")
async def get_inbox(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("student", "parent", "tutor", "counselor", "owner", "admin")),
):
    """
    Returns notifications addressed canonically to current_user.id.
    """
    from sqlalchemy import select, and_
    from datetime import timezone
    stmt = (
        select(NotificationLog)
        .where(
            and_(
                NotificationLog.tenant_id == tenant.id,
                NotificationLog.recipient_id == str(current_user.id),
            )
        )
        .order_by(NotificationLog.created_at.desc())
    )
    result = await db.execute(stmt)
    logs = list(result.scalars().all())
    return {"success": True, "data": [NotificationLogOut.model_validate(l) for l in logs]}


@router.patch("/inbox/{log_id}/read")
async def mark_as_read(
    log_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("student", "parent", "tutor", "counselor", "owner", "admin")),
):
    """
    Marks a notification as read, validating canonical ownership (recipient_id == current_user.id).
    """
    from sqlalchemy import select, and_
    from datetime import datetime, timezone
    import uuid

    try:
        log_uuid = uuid.UUID(str(log_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Notification not found")

    stmt = (
        select(NotificationLog)
        .where(
            and_(
                NotificationLog.id == log_uuid,
                NotificationLog.tenant_id == tenant.id,
                NotificationLog.recipient_id == str(current_user.id),
            )
        )
    )
    log = (await db.execute(stmt)).scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Notification not found")

    log.read_at = datetime.now(timezone.utc)
    await db.flush()
    return {"success": True, "data": NotificationLogOut.model_validate(log)}