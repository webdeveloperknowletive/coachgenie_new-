import uuid
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, and_, func
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload                          # ← ADD THIS
from app.models.student import Student
from app.utils.exceptions import NotFoundError, ConflictError
from app.utils.pagination import paginate
from datetime import date


# async def get_students(db: AsyncSession, tenant_id: str, page: int,
#                        limit: int, search: str | None = None) -> dict:
#     # conditions = [Student.tenant_id == tenant_id, Student.is_active == True]
#     conditions = [
#     Student.tenant_id == tenant_id
# ]
#     if search:
#         conditions.append(Student.first_name.ilike(f"%{search}%"))

#     total = (await db.execute(
#         select(func.count()).select_from(Student).where(and_(*conditions))
#     )).scalar()

#     result = await db.execute(
#         select(Student)
#         .options(selectinload(Student.batch_enrollments))        # ← ADD THIS
#         .where(and_(*conditions))
#         .order_by(Student.created_at.desc())
#         .offset((page - 1) * limit).limit(limit)
#     )
#     return paginate(result.scalars().all(), total, page, limit)
async def get_students(db: AsyncSession, tenant_id: str, page: int,limit: int, search: str | None = None)-> dict:

    conditions = [
        Student.tenant_id == tenant_id
    ]

    if search:
        conditions.append(
            or_(
                Student.first_name.ilike(f"%{search}%"),
                Student.last_name.ilike(f"%{search}%"),
                Student.email.ilike(f"%{search}%"),
                Student.phone.ilike(f"%{search}%"),
                Student.enrollment_no.ilike(f"%{search}%"),
            )
        )

    total = (
        await db.execute(
            select(func.count())
            .select_from(Student)
            .where(and_(*conditions))
        )
    ).scalar()

    result = await db.execute(
        select(Student)
        .options(selectinload(Student.batch_enrollments))
        .where(and_(*conditions))
        .order_by(Student.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )

    return paginate(result.scalars().all(), total, page, limit)


async def get_student(db: AsyncSession, tenant_id: str, student_id: str) -> Student:
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.batch_enrollments))        # ← ADD THIS
        .where(
            and_(Student.id == student_id, Student.tenant_id == tenant_id)
        )
    )
    student = result.scalar_one_or_none()
    if not student:
        raise NotFoundError("Student")
    return student


async def create_student(
    db: AsyncSession,
    tenant_id: str,
    data: dict
) -> Student:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    
    # Server-side subscription quota verification
    from app.models.tenant import Tenant
    from app.services.entitlement import check_quota
    tenant_obj = await db.get(Tenant, t_uuid)
    if tenant_obj:
        await check_quota(db, tenant_obj, "students", increment=1)

    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    enrollment_no = (data.get("enrollment_no") or "").strip()

    dup_conditions = []
    if email:
        dup_conditions.append(func.lower(Student.email) == email)
    if phone:
        dup_conditions.append(Student.phone == phone)
    if enrollment_no:
        dup_conditions.append(Student.enrollment_no == enrollment_no)

    if dup_conditions:
        existing = await db.scalar(
            select(Student.id).where(
                and_(
                    Student.tenant_id == t_uuid,
                    or_(*dup_conditions)
                )
            )
        )
        if existing:
            raise ConflictError("A student with this email, phone number, or enrollment number already exists in this institute.")

    if not enrollment_no:
        from app.services.admission import next_enrollment_no
        enrollment_no = await next_enrollment_no(db, str(t_uuid))

    student = Student(
        id=uuid.uuid4(),
        tenant_id=t_uuid,
        enrollment_no=enrollment_no,
        first_name=data.get("first_name", "Student"),
        last_name=data.get("last_name", ""),
        email=email or None,
        phone=phone or None,
        parent_name=data.get("parent_name"),
        parent_phone=data.get("parent_phone"),
        parent_email=data.get("parent_email"),
        current_class=data.get("current_class") or data.get("grade") or "",
        address=data.get("address"),
        city=data.get("city"),
        state=data.get("state"),
        pincode=data.get("pincode"),
        date_of_birth=data.get("date_of_birth") or data.get("dob"),
        gender=data.get("gender"),
        target_exam=data.get("target_exam") or data.get("targetExam"),
        school_name=data.get("school_name") or data.get("schoolName"),
        subjects=data.get("subjects") or [],
        custom_fields=data.get("custom_fields") or {},
        is_active=data.get("is_active", True),
        joined_at=date.today(),
    )
    db.add(student)
    await db.flush()
    return student


async def update_student(
    db: AsyncSession,
    tenant_id: str,
    student_id: str,
    data: dict
) -> Student:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    student = await get_student(db, str(t_uuid), student_id)

    new_email = (data.get("email") or "").strip().lower() if "email" in data and data["email"] is not None else None
    new_phone = (data.get("phone") or "").strip() if "phone" in data and data["phone"] is not None else None
    new_enr = (data.get("enrollment_no") or "").strip() if "enrollment_no" in data and data["enrollment_no"] is not None else None

    dup_conditions = []
    if new_email and new_email != (student.email or "").lower():
        dup_conditions.append(func.lower(Student.email) == new_email)
    if new_phone and new_phone != student.phone:
        dup_conditions.append(Student.phone == new_phone)
    if new_enr and new_enr != student.enrollment_no:
        dup_conditions.append(Student.enrollment_no == new_enr)

    if dup_conditions:
        existing = await db.scalar(
            select(Student.id).where(
                and_(
                    Student.tenant_id == t_uuid,
                    Student.id != student.id,
                    or_(*dup_conditions)
                )
            )
        )
        if existing:
            raise ConflictError("Another student with this email, phone number, or enrollment number already exists in this institute.")

    allowed_fields = {
        "first_name", "last_name", "email", "phone", "enrollment_no",
        "current_class", "date_of_birth", "parent_name", "parent_phone",
        "gender", "address", "city", "state", "pincode", "parent_email",
        "school_name", "target_exam", "subjects", "is_active", "custom_fields",
    }

    for key, value in data.items():
        if key in allowed_fields and value is not None:
            setattr(student, key, value)

    # flush to write changes; get_db() will commit on clean exit.
    await db.flush()
    await db.refresh(student, ["batch_enrollments"])
    return student


async def deactivate_student(db: AsyncSession, tenant_id: str, student_id: str):
    student = await get_student(db, tenant_id, student_id)
    student.is_active = False
    await db.flush()  # get_db() commits on clean exit.
    await db.refresh(student)
    return student


async def get_student_portal_dashboard(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    current_user: "User",
) -> dict:
    from decimal import Decimal
    from app.models.batch import Batch, BatchStudent, Class
    from app.models.fee import FeeInvoice
    from app.models.exam import Exam
    from app.models.notification import NotificationLog
    from app.services.attendance import get_student_summary
    from app.services.exam import get_results_for_student
    from app.utils.exceptions import NotFoundError

    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    
    st_stmt = (
        select(Student)
        .where(
            and_(
                Student.tenant_id == t_uuid,
                Student.user_id == current_user.id,
            )
        )
    )
    student = (await db.execute(st_stmt)).scalars().first()
    if not student:
        raise NotFoundError("Student profile linked to this user")

    st_id = student.id

    # 1. Batches & Schedule
    b_stmt = (
        select(Batch)
        .join(BatchStudent, BatchStudent.batch_id == Batch.id)
        .where(
            and_(
                Batch.tenant_id == t_uuid,
                BatchStudent.student_id == st_id,
                Batch.is_active == True,
            )
        )
    )
    batches = list((await db.execute(b_stmt)).scalars().all())
    batch_ids = [b.id for b in batches]

    # Upcoming classes
    upcoming_classes = []
    if batch_ids:
        c_stmt = (
            select(Class)
            .where(
                and_(
                    Class.tenant_id == t_uuid,
                    Class.batch_id.in_(batch_ids),
                )
            )
            .order_by(Class.scheduled_at.asc())
            .limit(10)
        )
        upcoming_classes = list((await db.execute(c_stmt)).scalars().all())

    # 2. Attendance Summary
    att_summary = await get_student_summary(db, str(t_uuid), str(st_id))

    # 3. Published Exam Results
    exam_results = await get_results_for_student(db, str(t_uuid), str(st_id), is_published_only=True)

    # 4. Fees
    f_stmt = (
        select(FeeInvoice)
        .where(
            and_(
                FeeInvoice.tenant_id == t_uuid,
                FeeInvoice.student_id == st_id,
            )
        )
        .order_by(FeeInvoice.due_date.asc())
    )
    invoices = list((await db.execute(f_stmt)).scalars().all())
    total_due = sum(Decimal(str(i.amount_due)) for i in invoices)
    total_paid = sum(Decimal(str(i.amount_paid)) for i in invoices)
    balance = max(Decimal("0.00"), total_due - total_paid)

    # 5. Notifications
    n_stmt = (
        select(NotificationLog)
        .where(
            and_(
                NotificationLog.tenant_id == t_uuid,
                NotificationLog.recipient_id == str(current_user.id),
            )
        )
        .order_by(NotificationLog.created_at.desc())
        .limit(10)
    )
    notifs = list((await db.execute(n_stmt)).scalars().all())

    return {
        "student": {
            "id": str(student.id),
            "first_name": student.first_name,
            "last_name": student.last_name,
            "enrollment_no": student.enrollment_no,
            "email": student.email,
            "phone": student.phone,
            "current_class": student.current_class,
            "target_exam": student.target_exam,
            "photo_url": student.photo_url,
            "school_name": student.school_name,
            "parent_name": student.parent_name,
        },
        "batches": [
            {
                "id": str(b.id),
                "name": b.name,
                "academic_year": b.academic_year,
            }
            for b in batches
        ],
        "today_classes": [
            {
                "id": str(c.id),
                "batch_id": str(c.batch_id),
                "title": c.title,
                "scheduled_at": str(c.scheduled_at),
                "duration_min": c.duration_min,
                "room_or_link": c.room_or_link,
                "status": c.status,
            }
            for c in upcoming_classes
        ],
        "attendance": att_summary,
        "fees": {
            "total_due": float(total_due),
            "total_paid": float(total_paid),
            "balance": float(balance),
            "invoices": [
                {
                    "id": str(i.id),
                    "invoice_no": i.invoice_no,
                    "amount_due": float(i.amount_due),
                    "amount_paid": float(i.amount_paid),
                    "due_date": str(i.due_date),
                    "status": i.status,
                }
                for i in invoices
            ],
        },
        "exams": [
            {
                "id": str(e.id),
                "exam_id": str(e.exam_id),
                "marks_obtained": float(e.marks_obtained),
                "grade": e.grade,
                "rank_in_batch": e.rank_in_batch,
                "remarks": e.remarks,
            }
            for e in exam_results
        ],
        "notifications": [
            {
                "id": str(n.id),
                "subject": n.subject,
                "body": n.body,
                "channel": n.channel,
                "read_at": str(n.read_at) if n.read_at else None,
                "created_at": str(n.created_at),
            }
            for n in notifs
        ],
    }


async def get_student_portal_timetable(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    current_user: "User",
) -> list[dict]:
    from app.models.batch import Batch, BatchStudent, Class
    from app.utils.exceptions import NotFoundError

    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    
    st_stmt = select(Student.id).where(
        and_(Student.tenant_id == t_uuid, Student.user_id == current_user.id)
    )
    student_id = (await db.execute(st_stmt)).scalar_one_or_none()
    if not student_id:
        raise NotFoundError("Student profile linked to this user")

    # Enrolled batches
    b_stmt = select(BatchStudent.batch_id).where(BatchStudent.student_id == student_id)
    batch_ids = list((await db.execute(b_stmt)).scalars().all())

    if not batch_ids:
        return []

    c_stmt = (
        select(Class)
        .where(
            and_(
                Class.tenant_id == t_uuid,
                Class.batch_id.in_(batch_ids),
            )
        )
        .order_by(Class.scheduled_at.asc())
    )
    classes = list((await db.execute(c_stmt)).scalars().all())

    return [
        {
            "id": str(c.id),
            "batch_id": str(c.batch_id),
            "title": c.title,
            "scheduled_at": str(c.scheduled_at),
            "duration_min": c.duration_min,
            "room_or_link": c.room_or_link,
            "status": c.status,
        }
        for c in classes
    ]