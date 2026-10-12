from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, and_
from app.dependencies import get_tenant, require_roles, DB
from app.schemas.student import StudentCreate, StudentUpdate, StudentOut
from app.models.student import Student
from app.models.user import User
from app.services import student as student_service

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/", status_code=201)
async def create_student(
    body: StudentCreate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    student = await student_service.create_student(db, str(tenant.id), data)
    return {"success": True, "data": StudentOut.model_validate(student)}


@router.get("/")
async def list_students(
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor", "tutor")),
):
    result = await student_service.get_students(db, str(tenant.id), page, limit, search)
    return {"success": True, **result}



@router.get("/portal/dashboard")
async def student_dashboard(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("student")),
):
    """
    Returns student profile, enrolled batches, today's classes, attendance summary,
    published exam results, fee balances, and notifications in one optimized call.
    Derived 100% from authenticated session; no client student_id accepted.
    """
    data = await student_service.get_student_portal_dashboard(db, str(tenant.id), current_user)
    return {"success": True, "data": data}


@router.get("/portal/timetable")
async def student_timetable(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("student")),
):
    """
    Returns the scheduled timetable across all enrolled batches for the authenticated student.
    """
    data = await student_service.get_student_portal_timetable(db, str(tenant.id), current_user)
    return {"success": True, "data": data}


@router.get("/{student_id}")
async def get_student(
    student_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor", "tutor", "parent", "student")),
):
    if current_user.role == "student":
        res = await db.execute(
            select(Student).where(
                and_(Student.tenant_id == tenant.id, Student.user_id == current_user.id)
            )
        )
        linked = res.scalar_one_or_none()
        if not linked or str(linked.id) != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == "parent":
        from app.services.parent import verify_parent_child_access
        await verify_parent_child_access(db, str(tenant.id), current_user, student_id)

    student = await student_service.get_student(db, str(tenant.id), student_id)
    return {"success": True, "data": StudentOut.model_validate(student)}

@router.patch("/{student_id}")
async def update_student(
    student_id: str,
    body: StudentUpdate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "counselor")),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    student = await student_service.update_student(db, str(tenant.id), student_id, data)
    return {"success": True, "data": StudentOut.model_validate(student)}

@router.delete("/{student_id}")
async def deactivate_student(
    student_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner")),
):
    await student_service.deactivate_student(db, str(tenant.id), student_id)
    return {"success": True, "message": "Student deactivated."}
