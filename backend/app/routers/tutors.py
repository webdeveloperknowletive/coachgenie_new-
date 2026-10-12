from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.dependencies import get_tenant, require_roles, DB
from app.models.user import User

router = APIRouter(prefix="/tutors", tags=["Tutors"])

@router.get("/")
async def list_tutors(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin", "counselor")),
):
    result = await db.execute(
        select(User).where(User.tenant_id == str(tenant.id), User.role == "tutor")
    )
    users = result.scalars().all()
    return {"success": True, "data": [
        {k: v for k, v in u.__dict__.items() if not k.startswith("_")}
        for u in users
    ]}


@router.get("/workspace")
async def tutor_workspace(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "admin", "tutor")),
):
    import uuid
    from datetime import date
    from app.models.batch import Batch, Class, BatchStudent
    from app.models.exam import Exam
    from app.models.syllabus import SyllabusProgress
    from sqlalchemy import and_, func

    t_uuid = uuid.UUID(str(tenant.id)) if isinstance(tenant.id, (str, uuid.UUID)) else tenant.id
    u_uuid = uuid.UUID(str(current_user.id)) if isinstance(current_user.id, (str, uuid.UUID)) else current_user.id
    is_admin = current_user.role in ("owner", "admin")

    # 1. Classes assigned to tutor (or all classes for today if owner/admin)
    class_conds = [Class.tenant_id == t_uuid]
    if not is_admin:
        class_conds.append(Class.tutor_id == u_uuid)

    classes_res = await db.execute(
        select(Class)
        .where(and_(*class_conds))
        .order_by(Class.scheduled_at.asc())
    )
    classes = classes_res.scalars().all()

    classes_data = []
    batch_ids = set()
    for c in classes:
        batch_ids.add(c.batch_id)
        classes_data.append({
            "id": str(c.id),
            "batch_id": str(c.batch_id),
            "subject_id": str(c.subject_id) if c.subject_id else None,
            "tutor_id": str(c.tutor_id) if c.tutor_id else None,
            "title": c.title,
            "room_or_link": c.room_or_link,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "duration_min": c.duration_min,
            "status": c.status,
        })

    # 2. Batches
    batches_data = []
    if batch_ids:
        batches_res = await db.execute(
            select(Batch).where(and_(Batch.tenant_id == t_uuid, Batch.id.in_(list(batch_ids))))
        )
        for b in batches_res.scalars().all():
            st_count = await db.scalar(
                select(func.count(BatchStudent.student_id)).where(BatchStudent.batch_id == b.id)
            ) or 0
            # Syllabus completion
            total_topics = await db.scalar(
                select(func.count(SyllabusProgress.id)).where(SyllabusProgress.batch_id == b.id)
            ) or 0
            completed_topics = await db.scalar(
                select(func.count(SyllabusProgress.id)).where(
                    and_(SyllabusProgress.batch_id == b.id, SyllabusProgress.status == "completed")
                )
            ) or 0
            progress_pct = round((completed_topics / total_topics * 100), 1) if total_topics > 0 else 0.0

            batches_data.append({
                "id": str(b.id),
                "name": b.name,
                "academic_year": b.academic_year,
                "student_count": st_count,
                "syllabus_progress_pct": progress_pct,
            })

    # 3. Upcoming Exams
    exam_conds = [Exam.tenant_id == t_uuid]
    if batch_ids:
        exam_conds.append(Exam.batch_id.in_(list(batch_ids)))
    exams_res = await db.execute(
        select(Exam).where(and_(*exam_conds)).order_by(Exam.scheduled_at.asc()).limit(10)
    )
    exams_data = [
        {
            "id": str(e.id),
            "title": e.title,
            "type": e.type,
            "total_marks": float(e.total_marks),
            "scheduled_at": e.scheduled_at.isoformat() if e.scheduled_at else None,
            "is_published": e.is_published,
        }
        for e in exams_res.scalars().all()
    ]

    return {
        "success": True,
        "data": {
            "tutor_id": str(u_uuid),
            "classes": classes_data,
            "batches": batches_data,
            "upcoming_exams": exams_data,
        }
    }