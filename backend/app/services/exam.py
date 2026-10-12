from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.exam import Exam, ExamResult
from app.utils.exceptions import NotFoundError, ConflictError
from app.utils.pagination import paginate


def calculate_grade(marks: float, total: float) -> str:
    pct = (marks / total) * 100
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B+"
    if pct >= 60: return "B"
    if pct >= 50: return "C"
    if pct >= 35: return "D"
    return "F"


async def get_exams(db: AsyncSession, tenant_id: str, page: int,
                    limit: int, batch_id: str | None = None) -> dict:
    conditions = [Exam.tenant_id == tenant_id]
    if batch_id:
        conditions.append(Exam.batch_id == batch_id)

    total = (await db.execute(
        select(func.count()).select_from(Exam).where(and_(*conditions))
    )).scalar()

    result = await db.execute(
        select(Exam).where(and_(*conditions))
        .order_by(Exam.created_at.desc())
        .offset((page - 1) * limit).limit(limit)
    )
    return paginate(result.scalars().all(), total, page, limit)


async def get_exam(db: AsyncSession, tenant_id: str, exam_id: str) -> Exam:
    result = await db.execute(
        select(Exam).where(and_(Exam.id == exam_id, Exam.tenant_id == tenant_id))
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise NotFoundError("Exam")
    return exam


async def create_exam(db: AsyncSession, tenant_id: str,
                      created_by: str, data: dict) -> Exam:
    import uuid
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    title = (data.get("title") or "").strip()
    batch_id = data.get("batch_id")
    scheduled_at = data.get("scheduled_at")

    if title and batch_id:
        b_uuid = uuid.UUID(str(batch_id)) if isinstance(batch_id, (str, uuid.UUID)) else batch_id
        dup_conds = [
            Exam.tenant_id == t_uuid,
            Exam.batch_id == b_uuid,
            func.lower(Exam.title) == title.lower(),
        ]
        if scheduled_at:
            dup_conds.append(Exam.scheduled_at == scheduled_at)

        existing = await db.scalar(
            select(Exam.id).where(and_(*dup_conds))
        )
        if existing:
            raise ConflictError(f"An exam with the title '{title}' already exists for this batch.")

    exam = Exam(tenant_id=t_uuid, created_by=created_by, **data)
    db.add(exam)
    await db.flush()
    return exam


async def update_exam(db: AsyncSession, tenant_id: str,
                      exam_id: str, data: dict) -> Exam:
    import uuid
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    exam = await get_exam(db, str(t_uuid), exam_id)

    new_title = (data.get("title") or "").strip() if "title" in data and data["title"] is not None else None
    new_batch = data.get("batch_id") if "batch_id" in data and data["batch_id"] is not None else exam.batch_id
    new_sched = data.get("scheduled_at") if "scheduled_at" in data and data["scheduled_at"] is not None else exam.scheduled_at

    if new_title and (new_title != exam.title or new_batch != exam.batch_id or new_sched != exam.scheduled_at):
        b_uuid = uuid.UUID(str(new_batch)) if isinstance(new_batch, (str, uuid.UUID)) else new_batch
        existing = await db.scalar(
            select(Exam.id).where(
                and_(
                    Exam.tenant_id == t_uuid,
                    Exam.id != exam.id,
                    Exam.batch_id == b_uuid,
                    func.lower(Exam.title) == new_title.lower(),
                )
            )
        )
        if existing:
            raise ConflictError(f"Another exam with the title '{new_title}' already exists for this batch.")

    for key, value in data.items():
        if value is not None:
            setattr(exam, key, value)
    await db.flush()
    return exam


async def submit_results(db: AsyncSession, tenant_id: str,
                         exam_id: str, results: list) -> list:
    from app.utils.exceptions import BadRequestError
    exam = await get_exam(db, tenant_id, exam_id)
    created = []
    seen_students = set()

    for r in results:
        st_id = str(r.get("student_id") or "").strip()
        if not st_id or st_id in seen_students:
            continue
        seen_students.add(st_id)

        marks = float(r.get("marks_obtained", 0))
        if marks < 0 or marks > float(exam.total_marks):
            raise BadRequestError(
                f"Marks ({marks}) for student {st_id} must be between 0 and total marks ({exam.total_marks})."
            )

        existing = await db.scalar(
            select(ExamResult).where(
                and_(
                    ExamResult.exam_id == exam_id,
                    ExamResult.student_id == st_id
                )
            )
        )

        is_pass = marks >= float(exam.passing_marks)
        grade   = calculate_grade(marks, float(exam.total_marks))

        if existing:
            existing.marks_obtained = marks
            existing.grade = grade
            existing.is_pass = is_pass
            existing.remarks = r.get("remarks")
            result_obj = existing
        else:
            result_obj = ExamResult(
                tenant_id=tenant_id,
                exam_id=exam_id,
                student_id=st_id,
                marks_obtained=marks,
                grade=grade,
                is_pass=is_pass,
                remarks=r.get("remarks"),
            )
            db.add(result_obj)
        created.append(result_obj)

    await db.flush()

    # Assign ranks
    all_result = await db.execute(
        select(ExamResult).where(ExamResult.exam_id == exam_id)
        .order_by(ExamResult.marks_obtained.desc())
    )
    for rank, res in enumerate(all_result.scalars().all(), start=1):
        res.rank_in_batch = rank

    await db.flush()
    return created


async def publish_exam_results(
    db: AsyncSession,
    tenant_id: str,
    exam_id: str,
    actor_id: str | None = None,
) -> Exam:
    from app.services.audit import log_audit_event
    exam = await get_exam(db, tenant_id, exam_id)
    exam.is_published = True
    await db.flush()

    await log_audit_event(
        db,
        tenant_id=exam.tenant_id,
        actor_id=actor_id,
        action="PUBLISH_EXAM_MARKS",
        entity_type="exam",
        entity_id=str(exam.id),
        metadata={"title": exam.title, "batch_id": str(exam.batch_id)},
    )
    return exam


async def get_results(db: AsyncSession, tenant_id: str, exam_id: str, user_role: str | None = None) -> list:
    from app.utils.exceptions import ForbiddenError
    exam = await get_exam(db, tenant_id, exam_id)
    if user_role in ("student", "parent") and not exam.is_published:
        raise ForbiddenError("Exam results have not been published yet.")

    result = await db.execute(
        select(ExamResult).where(
            and_(ExamResult.exam_id == exam_id, ExamResult.tenant_id == tenant_id)
        ).order_by(ExamResult.rank_in_batch.asc())
    )
    return result.scalars().all()


async def get_results_for_student(
    db: AsyncSession,
    tenant_id: str,
    student_id: str,
    is_published_only: bool = True,
) -> list[ExamResult]:
    stmt = (
        select(ExamResult)
        .join(Exam, ExamResult.exam_id == Exam.id)
        .where(
            and_(
                ExamResult.tenant_id == tenant_id,
                ExamResult.student_id == student_id,
            )
        )
    )
    if is_published_only:
        stmt = stmt.where(Exam.is_published == True)

    stmt = stmt.order_by(ExamResult.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
