import uuid
from sqlalchemy import String, Boolean, Text, SmallInteger, Numeric, Date, ForeignKey, text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from app.database import Base


class FeeStructure(Base):
    __tablename__ = "fee_structures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    installments: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    tenant = relationship("Tenant", back_populates="fee_structures")
    invoices = relationship("FeeInvoice", back_populates="fee_structure")


class FeeInvoice(Base):
    __tablename__ = "fee_invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_no", name="uq_invoice_no"),
        Index("idx_inv_student", "student_id"),
        Index("idx_inv_due_status", "tenant_id", "due_date", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    fee_structure_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fee_structures.id", ondelete="SET NULL"), nullable=True)
    invoice_no: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_due: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    due_date = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

    student = relationship("Student", back_populates="fee_invoices")
    fee_structure = relationship("FeeStructure", back_populates="invoices")
    payments = relationship("FeePayment", back_populates="invoice", cascade="all, delete-orphan")
    installments = relationship("FeeInstallment", back_populates="invoice", cascade="all, delete-orphan", order_by="FeeInstallment.installment_no")


class FeeInstallment(Base):
    __tablename__ = "fee_installments"
    __table_args__ = (
        UniqueConstraint("invoice_id", "installment_no", name="uq_invoice_installment"),
        Index("idx_inst_tenant_due", "tenant_id", "due_date", "status"),
        Index("idx_inst_student", "student_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fee_invoices.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    installment_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_due: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    due_date = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

    invoice = relationship("FeeInvoice", back_populates="installments")
    student = relationship("Student")


class FeePayment(Base):
    __tablename__ = "fee_payments"
    __table_args__ = (
        Index("idx_pay_invoice", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fee_invoices.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="cash")
    transaction_ref: Mapped[str] = mapped_column(String(100), nullable=True)
    paid_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    received_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str] = mapped_column(String(300), nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    invoice = relationship("FeeInvoice", back_populates="payments")