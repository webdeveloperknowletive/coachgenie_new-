import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.utils.exceptions import ConflictError
from datetime import date
from app.models.batch import Class

async def get_heatmap(db: AsyncSession, tenant_id: str) -> dict:
    from app.models.attendance import AttendanceRecord
    from datetime import date, timedelta
    since = date.today() - timedelta(days=180)
    result = await db.execute(
        select(
            func.date(AttendanceRecord.created_at).label("day"),
            func.count(AttendanceRecord.id).label("sessions"),
        )
        .where(
            and_(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.status == "present",
                func.date(AttendanceRecord.created_at) >= since,
            )
        )
        .group_by("day")
    )
    return {str(r.day): min(r.sessions, 4) for r in result.all()}

async def get_attendance_by_batch(
    db: AsyncSession,
    tenant_id: str,
    batch_id: str,
    from_date: str,
    to_date: str,
) -> list:
    from datetime import date as date_type
    import uuid

    result = await db.execute(
        select(
            AttendanceRecord.student_id,
            AttendanceRecord.status,
            AttendanceSession.session_date,
        )
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .join(Class, AttendanceSession.class_id == Class.id)
        .where(
            and_(
                AttendanceSession.tenant_id == uuid.UUID(tenant_id),
                Class.batch_id == uuid.UUID(batch_id),
                AttendanceSession.session_date >= date_type.fromisoformat(from_date),
                AttendanceSession.session_date <= date_type.fromisoformat(to_date),
            )
        )
    )
    rows = result.all()

    # ✅ Deduplicate by student_id + date
    seen = set()
    unique_rows = []
    for r in rows:
        key = (str(r.student_id), str(r.session_date))
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)

    return [
        {
            "studentId": str(r.student_id),
            "batchId":   batch_id,
            "date":      str(r.session_date),
            "status":    r.status,
        }
        for r in unique_rows
    ]


async def take_attendance(db: AsyncSession, tenant_id: str, taken_by: str,
                          class_id: str, session_date: date, records: list):
    import uuid
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    c_uuid = uuid.UUID(str(class_id)) if isinstance(class_id, (str, uuid.UUID)) else class_id

    existing = await db.execute(
        select(AttendanceSession).where(
            and_(
                AttendanceSession.tenant_id == t_uuid,
                AttendanceSession.class_id == c_uuid,
                AttendanceSession.session_date == session_date
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Attendance already taken for this class on this date.")

    session = AttendanceSession(
        tenant_id=t_uuid,
        class_id=c_uuid,
        taken_by=uuid.UUID(str(taken_by)) if taken_by else None,
        session_date=session_date,
    )
    db.add(session)
    await db.flush()

    seen_student_ids = set()
    for record in records:
        raw_st_id = str(record.get("student_id") or "").strip()
        if not raw_st_id or raw_st_id in seen_student_ids:
            continue
        seen_student_ids.add(raw_st_id)

        att = AttendanceRecord(
            tenant_id=t_uuid,
            session_id=session.id,
            student_id=uuid.UUID(raw_st_id),
            status=record.get("status", "present"),
            remarks=record.get("remarks"),
        )
        db.add(att)

    await db.commit()
    return session


async def take_or_update_bulk_attendance(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    taken_by_user,
    class_id: str | uuid.UUID,
    session_date: date,
    records: list,
) -> AttendanceSession:
    """
    Rapid, authorization-hardened attendance entry.
    Verifies:
    1. Class belongs to tenant.
    2. Tutor is assigned to class/batch (unless owner/admin).
    3. Students are enrolled in class's batch.
    4. Upserts session and records safely with audit logging.
    """
    from app.models.batch import Class, BatchStudent
    from app.models.student import Student
    from app.services.audit import log_audit_event
    from app.utils.exceptions import NotFoundError, ForbiddenError, BadRequestError
    import uuid

    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    c_uuid = uuid.UUID(str(class_id)) if isinstance(class_id, (str, uuid.UUID)) else class_id
    u_uuid = uuid.UUID(str(taken_by_user.id)) if hasattr(taken_by_user, "id") else uuid.UUID(str(taken_by_user))

    # 1. Fetch Class
    cls = await db.scalar(
        select(Class).where(and_(Class.id == c_uuid, Class.tenant_id == t_uuid))
    )
    if not cls:
        raise NotFoundError("Class")

    # 2. Authorization check: Tutors can only take attendance for their own classes
    role_key = (getattr(taken_by_user, "role", "") or "").lower()
    if role_key == "tutor":
        if cls.tutor_id and cls.tutor_id != u_uuid:
            raise ForbiddenError("Tutors are only authorized to take attendance for their assigned classes.")

    # 3. Verify student enrollment in batch
    batch_students_res = await db.execute(
        select(BatchStudent.student_id).where(BatchStudent.batch_id == cls.batch_id)
    )
    enrolled_student_ids = {str(sid) for sid in batch_students_res.scalars().all()}

    # 4. Fetch or create AttendanceSession
    existing_session = await db.scalar(
        select(AttendanceSession).where(
            and_(
                AttendanceSession.tenant_id == t_uuid,
                AttendanceSession.class_id == c_uuid,
                AttendanceSession.session_date == session_date,
            )
        ).with_for_update()
    )

    is_update = bool(existing_session)
    if existing_session:
        session = existing_session
        session.taken_by = u_uuid
    else:
        session = AttendanceSession(
            id=uuid.uuid4(),
            tenant_id=t_uuid,
            class_id=c_uuid,
            taken_by=u_uuid,
            session_date=session_date,
        )
        db.add(session)
        await db.flush()

    # 5. Fetch existing records for session
    existing_records_res = await db.execute(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)
    )
    rec_by_student = {str(r.student_id): r for r in existing_records_res.scalars().all()}

    seen_students = set()
    for rec in records:
        st_id_str = str(rec.get("student_id") or "").strip()
        if not st_id_str or st_id_str in seen_students:
            continue
        seen_students.add(st_id_str)

        # Enforce batch membership if batch has enrolled students
        if enrolled_student_ids and st_id_str not in enrolled_student_ids:
            raise BadRequestError(f"Student '{st_id_str}' is not enrolled in the batch for this class.")

        st_uuid = uuid.UUID(st_id_str)
        status_val = rec.get("status", "present")
        remarks_val = rec.get("remarks")

        if st_id_str in rec_by_student:
            r_obj = rec_by_student[st_id_str]
            r_obj.status = status_val
            r_obj.remarks = remarks_val
        else:
            new_r = AttendanceRecord(
                id=uuid.uuid4(),
                tenant_id=t_uuid,
                session_id=session.id,
                student_id=st_uuid,
                status=status_val,
                remarks=remarks_val,
            )
            db.add(new_r)

    await db.flush()

    # 6. Audit log
    await log_audit_event(
        db,
        tenant_id=t_uuid,
        actor_id=u_uuid,
        action="ATTENDANCE_CORRECTED" if is_update else "ATTENDANCE_RECORDED",
        entity_type="attendance_session",
        entity_id=str(session.id),
        metadata={
            "class_id": str(c_uuid),
            "session_date": str(session_date),
            "records_count": len(seen_students),
        },
    )

    await db.commit()
    return session


async def get_sessions(db: AsyncSession, tenant_id: str, class_id: str) -> list:
    result = await db.execute(
        select(AttendanceSession).where(
            and_(
                AttendanceSession.class_id == class_id,
                AttendanceSession.tenant_id == tenant_id
            )
        ).order_by(AttendanceSession.session_date.desc())
    )
    return result.scalars().all()


async def get_student_summary(db: AsyncSession, tenant_id: str, student_id: str) -> dict:
    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.tenant_id == tenant_id
            )
        )
    )
    records = result.scalars().all()
    total = len(records)

    if total == 0:
        return {
            "student_id": student_id,
            "total_classes": 0,
            "present": 0,
            "absent": 0,
            "late": 0,
            "attendance_percent": 0.0
        }

    present = sum(1 for r in records if r.status == "present")
    absent  = sum(1 for r in records if r.status == "absent")
    late    = sum(1 for r in records if r.status == "late")

    return {
        "student_id": student_id,
        "total_classes": total,
        "present": present,
        "absent": absent,
        "late": late,
        "attendance_percent": round((present / total) * 100, 2),
    }
