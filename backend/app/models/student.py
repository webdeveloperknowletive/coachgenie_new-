import uuid
from sqlalchemy import String, Boolean, Text, Date, ForeignKey, text, UniqueConstraint, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from app.database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("tenant_id", "enrollment_no", name="uq_enrollment"),
        Index("idx_students_tenant", "tenant_id"),
        Index("idx_students_active", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parent_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    admission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admissions.id", ondelete="SET NULL"),
        nullable=True, unique=True, index=True,
    )
    joined_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=True)
    enrollment_no: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(10), nullable=True)
    blood_group: Mapped[str] = mapped_column(String(5), nullable=True)
    photo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str] = mapped_column(String(10), nullable=True)
    parent_name: Mapped[str] = mapped_column(String(150), nullable=True)
    parent_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    parent_email: Mapped[str] = mapped_column(String(255), nullable=True)
    school_name: Mapped[str] = mapped_column(String(200), nullable=True)
    current_class: Mapped[str] = mapped_column(String(50), nullable=True)
    target_exam: Mapped[str] = mapped_column(String(150), nullable=True)
    subjects: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    custom_fields: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    left_at = mapped_column(Date, nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

    tenant = relationship("Tenant", back_populates="students")
    batch_enrollments = relationship("BatchStudent", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    exam_results = relationship("ExamResult", back_populates="student", cascade="all, delete-orphan")
    fee_invoices = relationship("FeeInvoice", back_populates="student", cascade="all, delete-orphan")
    growth_cards = relationship("GrowthCard", back_populates="student", cascade="all, delete-orphan")
    ai_sessions = relationship("AISession", back_populates="student", cascade="all, delete-orphan")
    admission = relationship("Admission", foreign_keys="Student.admission_id", primaryjoin="Student.admission_id == Admission.id", lazy="select")
