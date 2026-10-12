import uuid
from datetime import date
from sqlalchemy import String, Boolean, Text, Date, SmallInteger, ForeignKey, text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_subject_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        Index("idx_batches_tenant", "tenant_id"),
        Index("idx_batches_active", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    target_exam: Mapped[str] = mapped_column(String(150), nullable=True)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date = mapped_column(Date, nullable=True)
    end_date = mapped_column(Date, nullable=True)
    capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")

    # ✅ NEW: weekly schedule stored as JSON array
    # e.g. [{"day": "Monday", "start_time": "09:00", "end_time": "10:30", "room_or_link": "Room 4"}]
    # schedule = mapped_column(JSONB, nullable=True, default=list)
    schedule = mapped_column(JSONB, nullable=True, default=list)
    subjects = mapped_column(JSONB, nullable=True, default=list)
    custom_fields = mapped_column(JSONB, nullable=True, default=dict)

    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

    tenant = relationship("Tenant", back_populates="batches")
    enrollments = relationship("BatchStudent", back_populates="batch", cascade="all, delete-orphan")
    classes = relationship("Class", back_populates="batch", cascade="all, delete-orphan")
    syllabus_progress = relationship("SyllabusProgress", back_populates="batch", cascade="all, delete-orphan")


class BatchStudent(Base):
    __tablename__ = "batch_students"
    __table_args__ = (
        Index("idx_bs_student", "student_id"),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    enrolled_at = mapped_column(Date, nullable=False, default=date.today)

    batch = relationship("Batch", back_populates="enrollments")
    student = relationship("Student", back_populates="batch_enrollments")


class Class(Base):
    __tablename__ = "classes"
    __table_args__ = (
        Index("idx_classes_batch", "batch_id"),
        Index("idx_classes_scheduled_at", "tenant_id", "scheduled_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    tutor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    scheduled_at = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    duration_min: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=60)
    room_or_link: Mapped[str] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

    batch = relationship("Batch", back_populates="classes")
    attendance_sessions = relationship("AttendanceSession", back_populates="cls", cascade="all, delete-orphan")
