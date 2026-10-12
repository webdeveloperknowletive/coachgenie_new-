from fastapi import APIRouter, Depends,Query
from app.dependencies import get_tenant, require_roles, DB
from app.schemas.attendance import TakeAttendanceRequest
from app.services import attendance as att_service


router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/heatmap")
async def attendance_heatmap(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor", "counselor")),
):
    from app.services.attendance import get_heatmap
    data = await get_heatmap(db, str(tenant.id))
    return {"success": True, "data": data}

@router.get("/")
async def get_attendance_by_batch(
    batch_id: str,
    db: DB,  # FIX BUG-009: removed = None; moved before defaulted Query params
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor", "counselor")),
    from_date: str = Query(..., alias="from"),
    to_date: str   = Query(..., alias="to"),
):
    records = await att_service.get_attendance_by_batch(
        db, str(tenant.id), batch_id, from_date, to_date
    )
    return {"success": True, "data": records}

@router.post("/", status_code=201)
async def take_attendance(
    body: TakeAttendanceRequest,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor")),
):
    records = [{"student_id": str(r.student_id), "status": r.status, "remarks": r.remarks} for r in body.records]
    session = await att_service.take_attendance(
        db, str(tenant.id), str(current_user.id), str(body.class_id), body.session_date, records
    )
    return {"success": True, "data": {"session_id": str(session.id)}}


@router.post("/bulk", status_code=200)
async def take_or_update_bulk(
    body: TakeAttendanceRequest,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin", "tutor")),
):
    records = [{"student_id": str(r.student_id), "status": r.status, "remarks": r.remarks} for r in body.records]
    session = await att_service.take_or_update_bulk_attendance(
        db,
        str(tenant.id),
        current_user,
        str(body.class_id),
        body.session_date,
        records,
    )
    return {"success": True, "data": {"session_id": str(session.id), "session_date": str(session.session_date)}}

@router.get("/class/{class_id}")
async def list_sessions(
    class_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor", "counselor")),
):
    sessions = await att_service.get_sessions(db, str(tenant.id), class_id)
    return {"success": True, "data": [{"id": str(s.id), "session_date": str(s.session_date)} for s in sessions]}

@router.get("/student/{student_id}/summary")
async def student_summary(
    student_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor", "counselor", "parent", "student")),
):
    """
    FIX: Added ownership check — students can only see their own attendance;
    parents can only see their linked child's attendance.
    Staff roles (owner, tutor, counselor) retain unrestricted access.
    """
    from fastapi import HTTPException
    from sqlalchemy import select, and_
    from app.models.student import Student

    if current_user.role == "student":
        result = await db.execute(
            select(Student).where(
                and_(Student.tenant_id == tenant.id, Student.user_id == current_user.id)
            )
        )
        linked = result.scalar_one_or_none()
        if not linked or str(linked.id) != student_id:
            raise HTTPException(status_code=403, detail="Access denied")

    elif current_user.role == "parent":
        from app.services.parent import verify_parent_child_access
        await verify_parent_child_access(db, str(tenant.id), current_user, student_id)

    # Staff roles (owner, tutor, counselor) — unrestricted access, fall through.

    summary = await att_service.get_student_summary(db, str(tenant.id), student_id)
    return {"success": True, "data": summary}
