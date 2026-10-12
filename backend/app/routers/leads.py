from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from app.dependencies import get_tenant, require_roles, DB
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadOut,
    ActivityCreate,
    ActivityOut,
    CRMPipelineConfig,
)
from app.services import lead as lead_service
from app.services import admission as admission_service
from app.services.inbox_notification import create_notification
from app.utils.exceptions import ConflictError, NotFoundError
from fastapi import Request


router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("/funnel")
async def lead_funnel(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    from app.services.lead import get_funnel
    data = await get_funnel(db, str(tenant.id))
    return {"success": True, "data": data}


@router.get("/pipeline/config")
async def get_pipeline_config(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin", "counselor")),
):
    config = await lead_service.get_crm_pipeline(db, str(tenant.id))
    return {"success": True, "data": config}


@router.put("/pipeline/config")
async def update_pipeline_config(
    request: Request,
    body: CRMPipelineConfig,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    ip_addr = request.client.host if request.client else None
    updated = await lead_service.update_crm_pipeline(
        db,
        str(tenant.id),
        body.model_dump(),
        actor_id=str(current_user.id),
        ip_address=ip_addr,
    )
    return {"success": True, "data": updated}





# ── List / CRUD ────────────────────────────────────────────────────────────────
@router.get("/")
async def list_leads(
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = Query(None),
    batch_id: str | None = Query(None),
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    result = await lead_service.get_leads(
        db, str(tenant.id), page, limit, status, search, batch_id=batch_id,
    )
    return {"success": True, **result}


# @router.post("/", status_code=201)
# async def create_lead(
#     body: LeadCreate,
#     db: DB,
#     tenant=Depends(get_tenant),
#     current_user=Depends(require_roles("owner", "counselor")),
# ):
#     data = body.model_dump()
#     if data.get("assigned_to"):
#         data["assigned_to"] = str(data["assigned_to"])
#     if data.get("batch_id"):
#         data["batch_id"] = str(data["batch_id"])
#     lead = await lead_service.create_lead(db, str(tenant.id), data)


#     print("RAW BODY:", await request.json())
#     print("PARSED:", body.model_dump())


#     # ── Inbox notification ──────────────────────────────────────────────────
#     await create_notification(
#         db,
#         tenant_id=str(tenant.id),
#         title="New lead added",
#         body=f"{lead.full_name} was added via {lead.source or 'unknown source'}",
#         icon="lead",
#         link=f"/leads/{lead.id}",
#     )
#     # ───────────────────────────────────────────────────────────────────────

#     await db.commit()
#     return {"success": True, "data": LeadOut.model_validate(lead)}

@router.post("/", status_code=201)
async def create_lead(
    body: LeadCreate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    data = body.model_dump()

    if data.get("assigned_to"):
        data["assigned_to"] = str(data["assigned_to"])

    if data.get("batch_id"):
        data["batch_id"] = str(data["batch_id"])

    lead = await lead_service.create_lead(
        db,
        str(tenant.id),
        data,
    )

    # ── Initial Activity Log ────────────────────────────────────────────
    await lead_service.add_activity(
        db,
        str(tenant.id),
        str(lead.id),
        str(current_user.id) if current_user else None,
        {
            "type": "NOTE",
            "description": f"Lead created via {(lead.source or 'website').replace('_', ' ').title()}",
        },
    )

    # ── Inbox notification ───────────────────────────────────────────────
    await create_notification(
        db,
        tenant_id=str(tenant.id),
        title="New lead added",
        body=f"{lead.full_name} was added via {lead.source or 'unknown source'}",
        icon="lead",
        link=f"/leads/{lead.id}",
    )
    # ────────────────────────────────────────────────────────────────────

    # db.commit() removed — get_db() context manager handles the commit.
    return {
        "success": True,
        "data": LeadOut.model_validate(lead),
    }

@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    lead = await lead_service.get_lead(db, str(tenant.id), lead_id)
    return {"success": True, "data": LeadOut.model_validate(lead)}


@router.patch("/{lead_id}")
async def update_lead(
    lead_id: str,
    body: LeadUpdate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if data.get("batch_id"):
        data["batch_id"] = str(data["batch_id"])
    lead = await lead_service.update_lead(db, str(tenant.id), lead_id, data)

    # ── Notify & Log on stage change ─────────────────────────────────────────
    if "status" in data:
        await lead_service.add_activity(
            db,
            str(tenant.id),
            lead_id,
            str(current_user.id) if current_user else None,
            {
                "type": "STAGE_CHANGE",
                "description": f"Stage updated to {data['status'].upper().replace('_', ' ')}",
            },
        )
        await create_notification(
            db,
            tenant_id=str(tenant.id),
            title="Lead stage updated",
            body=f"{lead.full_name} moved to {data['status'].upper()}",
            icon="lead",
            link=f"/leads/{lead.id}",
        )
    # ───────────────────────────────────────────────────────────────────────

    # db.commit() removed — get_db() handles commit.
    return {"success": True, "data": LeadOut.model_validate(lead)}


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner")),
):
    await lead_service.delete_lead(db, str(tenant.id), lead_id)
    # db.commit() removed — get_db() handles commit.
    return {"success": True, "message": "Lead deleted."}


# ── Pipeline actions ───────────────────────────────────────────────────────────

class AssignCounselorBody(BaseModel):
    counselor_id: str

@router.post("/{lead_id}/assign-counselor")
async def assign_counselor(
    lead_id: str,
    body: AssignCounselorBody,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    lead = await lead_service.update_lead(
        db, str(tenant.id), lead_id,
        {"assigned_to": body.counselor_id}
    )

    await create_notification(
        db,
        tenant_id=str(tenant.id),
        title="Lead assigned",
        body=f"{lead.full_name} was assigned to a counselor",
        icon="lead",
        link=f"/leads/{lead.id}",
        user_id=body.counselor_id,   # notify only the assigned counselor
    )
    # db.commit() removed — get_db() handles commit.
    return {"success": True, "message": "Counselor assigned.", "data": LeadOut.model_validate(lead)}


class ChangeStageBody(BaseModel):
    stage: str  # new / contacted / interested / converted / lost

@router.post("/{lead_id}/change-stage")
async def change_stage(
    lead_id: str,
    body: ChangeStageBody,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    valid_stages = {"new", "contacted", "interested", "demo_scheduled", "demo_done", "negotiation", "enrolled", "lost"}
    if body.stage not in valid_stages:
        raise HTTPException(status_code=422, detail=f"Invalid stage. Must be one of: {valid_stages}")
    lead = await lead_service.update_lead(
        db, str(tenant.id), lead_id, {"status": body.stage}
    )
    await lead_service.add_activity(
        db,
        str(tenant.id),
        lead_id,
        str(current_user.id) if current_user else None,
        {
            "type": "STAGE_CHANGE",
            "description": f"Stage changed to {body.stage.upper().replace('_', ' ')}",
        },
    )
    await create_notification(
        db,
        tenant_id=str(tenant.id),
        title="Lead stage changed",
        body=f"{lead.full_name} moved to {body.stage.upper()}",
        icon="lead",
        link=f"/leads/{lead.id}",
    )
    # db.commit() removed — get_db() handles commit.
    return {"success": True, "message": f"Stage updated to '{body.stage}'.", "data": LeadOut.model_validate(lead)}


class ScheduleFollowupBody(BaseModel):
    follow_up_date: date
    notes: Optional[str] = None

@router.post("/{lead_id}/schedule-followup")
async def schedule_followup(
    lead_id: str,
    body: ScheduleFollowupBody,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    lead = await lead_service.update_lead(
        db, str(tenant.id), lead_id,
        {"follow_up_date": body.follow_up_date}
    )
    if body.notes:
        await lead_service.add_activity(
            db, str(tenant.id), lead_id, str(current_user.id) if current_user else None,
            {"type": "follow_up_scheduled", "description": body.notes}
        )

    await create_notification(
        db,
        tenant_id=str(tenant.id),
        title="Follow-up scheduled",
        body=f"Follow-up for {lead.full_name} on {body.follow_up_date}",
        icon="lead",
        link=f"/leads/{lead.id}",
    )




    # db.commit() removed — get_db() handles commit.
    return {"success": True, "message": "Follow-up scheduled.", "data": LeadOut.model_validate(lead)}


class ConvertLeadBody(BaseModel):
    applied_course: Optional[str] = None
    academic_year: Optional[str] = None
    remarks: Optional[str] = None
    fee_amount: Optional[float] = None
    fee_paid: Optional[float] = None
    payment_mode: Optional[str] = None
    payment_installment_schedule: Optional[Any] = None

@router.post("/{lead_id}/convert", status_code=201)
async def convert_lead(
    lead_id: str,
    body: ConvertLeadBody,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):

    """
    Single conversion endpoint. Atomically:
      1. Creates admission from lead data
      2. Auto-approves it
      3. Generates a student record
      4. Marks lead as converted
    """



    try:
        admission, student = await admission_service.convert_lead(
            db,
            tenant_id    = str(tenant.id),
            lead_id      = lead_id,
            converted_by = str(current_user.id),
            admission_data = {k: v for k, v in body.model_dump().items() if v is not None},
        )





        # ── Inbox notification ──────────────────────────────────────────────
        await create_notification(
            db,
            tenant_id=str(tenant.id),
            title="Lead converted to admission",
            # body=f"{student.full_name} enrolled — admission {admission.admission_number}",
            body=f"{student.first_name} {student.last_name} enrolled — admission {admission.admission_number}",
            icon="admission",
            link=f"/admissions/{admission.id}",
        )
        # ───────────────────────────────────────────────────────────────────





        # db.commit() removed — get_db() handles commit.
        return {
            "success": True,
            "message": "Lead converted successfully.",
            "data": {
                "admission_id":     str(admission.id),
                "admission_number": admission.admission_number,
                "student_id":       str(student.id),
                "enrollment_no":    student.enrollment_no,
            }
        }
    except (ConflictError, NotFoundError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e.detail if hasattr(e, "detail") else e))
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")


# ── Activities ─────────────────────────────────────────────────────────────────
@router.post("/{lead_id}/activities", status_code=201)
async def add_activity(
    lead_id: str,
    body: ActivityCreate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    activity = await lead_service.add_activity(
        db, str(tenant.id), lead_id, str(current_user.id), body.model_dump()
    )
    activity.user = current_user
    # db.commit() removed — get_db() handles commit.
    return {"success": True, "data": ActivityOut.model_validate(activity)}


@router.get("/{lead_id}/activities")
async def list_activities(
    lead_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    activities = await lead_service.get_activities(db, str(tenant.id), lead_id)
    return {"success": True, "data": [ActivityOut.model_validate(a) for a in activities]}


