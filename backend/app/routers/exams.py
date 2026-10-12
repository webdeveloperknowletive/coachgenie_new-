from fastapi import APIRouter, Depends, Query
from app.dependencies import get_tenant, require_roles, DB
from app.schemas.exam import ExamCreate, ExamUpdate, ExamOut, BulkResultRequest, ExamResultOut
from app.services import exam as exam_service

router = APIRouter(prefix="/exams", tags=["Exams"])

@router.get("/")
async def list_exams(
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    batch_id: str | None = Query(None),
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor", "counselor", "student")),
):
    result = await exam_service.get_exams(db, str(tenant.id), page, limit, batch_id)
    return {"success": True, **result}

@router.post("/", status_code=201)
async def create_exam(
    body: ExamCreate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor")),
):
    data = body.model_dump()
    if data.get("batch_id"): data["batch_id"] = str(data["batch_id"])
    if data.get("subject_id"): data["subject_id"] = str(data["subject_id"])
    exam = await exam_service.create_exam(db, str(tenant.id), str(current_user.id), data)
    return {"success": True, "data": ExamOut.model_validate(exam)}

@router.patch("/{exam_id}")
async def update_exam(
    exam_id: str,
    body: ExamUpdate,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor")),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    exam = await exam_service.update_exam(db, str(tenant.id), exam_id, data)
    return {"success": True, "data": ExamOut.model_validate(exam)}

@router.post("/{exam_id}/results", status_code=201)
async def submit_results(
    exam_id: str,
    body: BulkResultRequest,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor")),
):
    results_data = [{"student_id": str(r.student_id), "marks_obtained": r.marks_obtained, "remarks": r.remarks} for r in body.results]
    results = await exam_service.submit_results(db, str(tenant.id), exam_id, results_data)
    return {"success": True, "data": [ExamResultOut.model_validate(r) for r in results]}


@router.post("/{exam_id}/publish", status_code=200)
async def publish_exam(
    exam_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin")),
):
    exam = await exam_service.publish_exam_results(db, str(tenant.id), exam_id, actor_id=str(current_user.id))
    return {"success": True, "data": ExamOut.model_validate(exam)}


@router.get("/{exam_id}/results")
async def get_results(
    exam_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin", "tutor", "counselor", "student", "parent")),
):
    results = await exam_service.get_results(db, str(tenant.id), exam_id, user_role=current_user.role)
    return {"success": True, "data": [ExamResultOut.model_validate(r) for r in results]}

from app.models.student import Student
from sqlalchemy import select, and_
from fastapi import HTTPException

@router.get("/student/{student_id}/results")
async def get_student_exam_results(
    student_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor", "counselor", "student", "parent")),
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

    is_pub_only = current_user.role in ("student", "parent")
    results = await exam_service.get_results_for_student(db, str(tenant.id), student_id, is_published_only=is_pub_only)
    return {"success": True, "data": [ExamResultOut.model_validate(r) for r in results]}