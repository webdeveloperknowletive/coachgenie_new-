import uuid
from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.models.student import Student
from app.models.user import User
from app.models.batch import Batch, BatchStudent, Class
from app.models.fee import FeeInvoice, FeePayment, FeeInstallment
from app.models.exam import Exam, ExamResult
from app.models.notification import NotificationLog
from app.services.attendance import get_student_summary
from app.services.exam import get_results_for_student
from app.utils.exceptions import ForbiddenError, NotFoundError


async def resolve_authorized_children(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    parent_user: User,
) -> list[Student]:
    """
    Resolves the authorized list of children for a parent user.
    Tier 1 (Canonical): Student.parent_user_id == parent_user.id
    Tier 2 (Scoped Fallback): Student.parent_email == parent_user.email OR parent_phone == parent_user.phone
    """
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    p_email = (parent_user.email or "").strip().lower()
    p_phone = (parent_user.phone or "").strip()

    fallback_conditions = []
    if p_email:
        fallback_conditions.append(func.lower(Student.parent_email) == p_email)
    if p_phone:
        fallback_conditions.append(Student.parent_phone == p_phone)

    conditions = [Student.parent_user_id == parent_user.id]
    if fallback_conditions:
        conditions.append(
            and_(
                Student.parent_user_id == None,
                or_(*fallback_conditions),
            )
        )

    stmt = (
        select(Student)
        .where(
            and_(
                Student.tenant_id == t_uuid,
                Student.is_active == True,
                or_(*conditions),
            )
        )
        .order_by(Student.first_name.asc(), Student.last_name.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def verify_parent_child_access(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    parent_user: User,
    student_id: str | uuid.UUID,
) -> Student:
    """
    Validates that the requested student_id is an authorized child of parent_user.
    Raises ForbiddenError if not authorized.
    """
    children = await resolve_authorized_children(db, tenant_id, parent_user)
    target_id_str = str(student_id).strip()
    for child in children:
        if str(child.id) == target_id_str:
            return child
    raise ForbiddenError("Access denied: Student is not linked to your parent account.")


async def get_parent_portal_dashboard(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    parent_user: User,
    requested_student_id: str | None = None,
) -> dict:
    """
    Aggregates the parent portal dashboard in a single optimized payload.
    """
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    children = await resolve_authorized_children(db, tenant_id, parent_user)

    # Select child
    selected_child: Student
    if requested_student_id:
        selected_child = await verify_parent_child_access(db, tenant_id, parent_user, requested_student_id)
    elif not children:
        return {
            "children": [],
            "selected_child": None,
            "batches": [],
            "attendance": {"total_classes": 0, "present": 0, "absent": 0, "late": 0, "percentage": 0.0},
            "fees": {"total_due": 0.0, "total_paid": 0.0, "balance": 0.0, "invoices": []},
            "exams": [],
            "notifications": [],
        }
    else:
        selected_child = children[0]

    st_id = selected_child.id

    # 1. Enrolled Batches
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
    batches_res = await db.execute(b_stmt)
    batches = list(batches_res.scalars().all())

    # 2. Attendance Summary
    att_summary = await get_student_summary(db, str(t_uuid), str(st_id))

    # 3. Fee summary and invoices
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
    invoices_res = await db.execute(f_stmt)
    invoices = list(invoices_res.scalars().all())

    total_due = sum(Decimal(str(i.amount_due)) for i in invoices)
    total_paid = sum(Decimal(str(i.amount_paid)) for i in invoices)
    balance = max(Decimal("0.00"), total_due - total_paid)

    # 4. Published Exam Results
    exams_data = await get_results_for_student(db, str(t_uuid), str(st_id), is_published_only=True)

    # 5. Parent Notifications (addressed to parent_user.id)
    n_stmt = (
        select(NotificationLog)
        .where(
            and_(
                NotificationLog.tenant_id == t_uuid,
                NotificationLog.recipient_id == str(parent_user.id),
            )
        )
        .order_by(NotificationLog.created_at.desc())
        .limit(10)
    )
    notifs_res = await db.execute(n_stmt)
    notifs = list(notifs_res.scalars().all())

    return {
        "children": [
            {
                "id": str(c.id),
                "first_name": c.first_name,
                "last_name": c.last_name,
                "enrollment_no": c.enrollment_no,
                "current_class": c.current_class,
                "photo_url": c.photo_url,
            }
            for c in children
        ],
        "selected_child": {
            "id": str(selected_child.id),
            "first_name": selected_child.first_name,
            "last_name": selected_child.last_name,
            "enrollment_no": selected_child.enrollment_no,
            "current_class": selected_child.current_class,
            "photo_url": selected_child.photo_url,
            "school_name": selected_child.school_name,
            "target_exam": selected_child.target_exam,
            "parent_name": selected_child.parent_name,
        },
        "batches": [
            {
                "id": str(b.id),
                "name": b.name,
                "academic_year": b.academic_year,
            }
            for b in batches
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
            for e in exams_data
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
