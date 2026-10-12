import uuid
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, distinct, or_

from app.models.student import Student
from app.models.batch import Batch, BatchStudent, Class
from app.models.lead import Lead
from app.models.admission import Admission
from app.models.exam import Exam, ExamResult
from app.models.fee import FeeInvoice, FeeInstallment
from app.models.attendance import AttendanceRecord
from app.models.growth_card import GrowthCard
from app.models.user import User


async def get_owner_dashboard(db: AsyncSession, tenant_id: str | uuid.UUID) -> dict:
    """
    Optimized executive dashboard metrics.
    Decoupled from redundant write-time syncs on read path.
    """
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id

    # 1. Total students (active)
    total_students = (await db.scalar(
        select(func.count(Student.id)).where(
            and_(Student.tenant_id == t_uuid, Student.is_active == True)
        )
    )) or 0

    # 2. Active batches
    active_batches = (await db.scalar(
        select(func.count(Batch.id)).where(
            and_(Batch.tenant_id == t_uuid, Batch.is_active == True)
        )
    )) or 0

    # 3. Leads metrics
    lead_stats = (await db.execute(
        select(
            func.count(Lead.id).label("total"),
            func.count(Lead.id).filter(Lead.status == "converted").label("converted"),
            func.count(Lead.id).filter(Lead.assigned_to == None).label("unassigned"),
        ).where(Lead.tenant_id == t_uuid)
    )).one()

    # 4. Revenue metrics (Invoices)
    revenue = (await db.execute(
        select(
            func.coalesce(func.sum(FeeInvoice.amount_due), 0).label("total"),
            func.coalesce(func.sum(FeeInvoice.amount_paid), 0).label("paid"),
        ).where(FeeInvoice.tenant_id == t_uuid)
    )).one()

    # 5. Overdue installments needing attention
    overdue_count = (await db.scalar(
        select(func.count(FeeInstallment.id)).where(
            and_(
                FeeInstallment.tenant_id == t_uuid,
                FeeInstallment.status.in_(["overdue", "pending", "partial"]),
                FeeInstallment.due_date < date.today(),
            )
        )
    )) or 0

    # 6. Total exams
    total_exams = (await db.scalar(
        select(func.count(Exam.id)).where(Exam.tenant_id == t_uuid)
    )) or 0

    # 7. Institute attendance aggregation (Single query)
    att_stats = (await db.execute(
        select(
            func.count(AttendanceRecord.id).label("total"),
            func.count(AttendanceRecord.id).filter(AttendanceRecord.status == "present").label("present"),
        ).where(AttendanceRecord.tenant_id == t_uuid)
    )).one()

    avg_attendance = round((att_stats.present / att_stats.total * 100), 2) if att_stats.total > 0 else 0.0

    return {
        "total_students": total_students,
        "active_batches": active_batches,
        "total_leads": lead_stats.total,
        "converted_leads": lead_stats.converted,
        "unassigned_leads": lead_stats.unassigned,
        "total_revenue": float(revenue.total),
        "total_collected": float(revenue.paid),
        "pending_revenue": float(revenue.total) - float(revenue.paid),
        "overdue_installments_count": overdue_count,
        "total_exams": total_exams,
        "avg_attendance_percent": avg_attendance,
    }


async def get_tutor_dashboard(db: AsyncSession, tenant_id: str | uuid.UUID, user_id: str | uuid.UUID) -> dict:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    u_uuid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
    today = date.today()

    # Classes today
    classes_today = (await db.scalar(
        select(func.count(Class.id)).where(
            and_(
                Class.tenant_id == t_uuid,
                Class.tutor_id == u_uuid,
                func.date(Class.scheduled_at) == today,
            )
        )
    )) or 0

    # Exams created by tutor
    exams_created = (await db.scalar(
        select(func.count(Exam.id)).where(
            and_(Exam.tenant_id == t_uuid, Exam.created_by == u_uuid)
        )
    )) or 0

    # Avg student score in tutor's exams
    avg_score = (await db.scalar(
        select(func.coalesce(func.avg(ExamResult.marks_obtained), 0)).where(
            ExamResult.tenant_id == t_uuid
        )
    )) or 0

    return {
        "my_batches": 0,
        "my_classes_today": classes_today,
        "total_students": 0,
        "exams_created": exams_created,
        "avg_student_score": round(float(avg_score), 2),
    }


async def get_student_dashboard(db: AsyncSession, tenant_id: str | uuid.UUID, student_id: str | uuid.UUID) -> dict:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    s_uuid = uuid.UUID(str(student_id)) if isinstance(student_id, str) else student_id

    # Attendance
    att_stats = (await db.execute(
        select(
            func.count(AttendanceRecord.id).label("total"),
            func.count(AttendanceRecord.id).filter(AttendanceRecord.status == "present").label("present"),
        ).where(
            and_(
                AttendanceRecord.tenant_id == t_uuid,
                AttendanceRecord.student_id == s_uuid,
            )
        )
    )).one()

    att_pct = round((att_stats.present / att_stats.total * 100), 2) if att_stats.total > 0 else 0.0

    # Exams
    exam_stats = (await db.execute(
        select(
            func.count(ExamResult.id).label("total"),
            func.coalesce(func.avg(ExamResult.marks_obtained), 0).label("avg_marks"),
        ).where(
            and_(
                ExamResult.tenant_id == t_uuid,
                ExamResult.student_id == s_uuid,
            )
        )
    )).one()

    # Pending fees
    pending = (await db.scalar(
        select(
            func.coalesce(
                func.sum(FeeInvoice.amount_due - FeeInvoice.amount_paid), 0
            )
        ).where(
            and_(
                FeeInvoice.tenant_id == t_uuid,
                FeeInvoice.student_id == s_uuid,
                FeeInvoice.status.in_(["pending", "partial", "overdue"]),
            )
        )
    )) or 0

    # Batches
    batches = (await db.scalar(
        select(func.count(BatchStudent.batch_id)).where(
            and_(
                BatchStudent.tenant_id == t_uuid,
                BatchStudent.student_id == s_uuid,
            )
        )
    )) or 0

    # Growth cards
    growth_cards = (await db.scalar(
        select(func.count(GrowthCard.id)).where(
            and_(
                GrowthCard.tenant_id == t_uuid,
                GrowthCard.student_id == s_uuid,
            )
        )
    )) or 0

    return {
        "my_batches": batches,
        "attendance_percent": att_pct,
        "total_exams": exam_stats.total,
        "avg_score": round(float(exam_stats.avg_marks), 2),
        "pending_fees": float(pending),
        "growth_cards": growth_cards,
    }


async def get_counselor_dashboard(db: AsyncSession, tenant_id: str | uuid.UUID) -> dict:
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id

    lead_stats = (await db.execute(
        select(
            func.count(Lead.id).label("total"),
            func.count(Lead.id).filter(Lead.status == "new").label("new_leads"),
            func.count(Lead.id).filter(Lead.status == "follow_up").label("follow_up"),
            func.count(Lead.id).filter(Lead.status == "converted").label("converted"),
        ).where(Lead.tenant_id == t_uuid)
    )).one()

    pending_admissions = (await db.scalar(
        select(func.count(Admission.id)).where(
            and_(
                Admission.tenant_id == t_uuid,
                Admission.status == "pending",
            )
        )
    )) or 0

    return {
        "total_leads": lead_stats.total,
        "new_leads": lead_stats.new_leads,
        "follow_up_leads": lead_stats.follow_up,
        "converted_leads": lead_stats.converted,
        "pending_admissions": pending_admissions,
    }
