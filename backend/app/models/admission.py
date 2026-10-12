import uuid
from sqlalchemy import String, Boolean, Text, ForeignKey, text, UniqueConstraint, Index, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from app.database import Base


class Admission(Base):
    __tablename__ = "admissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "admission_number", name="uq_admission_number"),
        Index("idx_admissions_tenant", "tenant_id"),
        Index("idx_admissions_status", "tenant_id", "status"),
        Index("idx_admissions_lead", "tenant_id", "lead_id"),  # added: common lookup path
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("batches.id", ondelete="SET NULL"),
    nullable=True,
    )

    admission_number: Mapped[str] = mapped_column(String(50), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING_DOCS"
    )
    applied_course: Mapped[str] = mapped_column(String(150), nullable=False)
    documents_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # FIX: approved_by and updated_by are both relevant — keep approved_by for
    # the approval workflow; add updated_by so service can write it.
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    approved_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()")
    )
    updated_at = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )

    # ── Student info (from frontend form) ─────────────────────────────────────
    student_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone:        Mapped[str | None] = mapped_column(String(20),  nullable=True)
    email:        Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_name:  Mapped[str | None] = mapped_column(String(150), nullable=True)
    parent_phone: Mapped[str | None] = mapped_column(String(20),  nullable=True)
    school_name:  Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    board_name:   Mapped[str | None] = mapped_column(String(100), nullable=True)  # ← ADD
    batch_name:   Mapped[str | None] = mapped_column(String(100), nullable=True)  # ← ADD
    subjects: Mapped[list] = mapped_column(JSON, nullable=True, default=list)

    # ── Fee fields (quick-access without parsing JSON) ─────────────────────────
    fee_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=0
    )
    fee_paid: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=0
    )

    # ── Payment + installment schedule stored as JSON string ──────────────────
    # Shape: { totalFee, amountPaid, remaining, paymentStatus, dateOfPayment,
    #          modeOfPayment, hasInstallments, numberOfInstallments,
    #          installmentAmount, installmentSchedule: [...], notes }
    payment_installment_schedule: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # ── Documents stored as JSON array ────────────────────────────────────────
    # Shape: [{ name, required, submitted }, ...]
    documents: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    custom_fields: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    # ── Relationships ──────────────────────────────────────────────────────────
    tenant = relationship("Tenant", back_populates="admissions")