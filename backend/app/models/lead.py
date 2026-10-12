import uuid
from sqlalchemy import String, Text, Date, ForeignKey, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from app.database import Base
from sqlalchemy import JSON

class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_leads_tenant", "tenant_id"),
        Index("idx_leads_status", "tenant_id", "status"),
        Index("idx_leads_follow", "tenant_id", "follow_up_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    assigned_to: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_name: Mapped[str] = mapped_column(String(150), nullable=True)
    parent_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    parent_contact_number: Mapped[str] = mapped_column(String(20), nullable=True)
    school_name: Mapped[str] = mapped_column(String(150), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="website")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    interested_course: Mapped[str] = mapped_column(String(150), nullable=True)
    grade: Mapped[str] = mapped_column(String(50), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    follow_up_date = mapped_column(Date, nullable=True)
    converted_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))
    documents: Mapped[list] = mapped_column(JSON, nullable=True, default=list)

    # ── NEW COLUMNS ──────────────────────────────────────────────────────────
    board_name: Mapped[str] = mapped_column(String(100), nullable=True)
    subjects: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    custom_fields: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── relationships ────────────────────────────────────────────────────────
    tenant = relationship("Tenant", back_populates="leads")
    activities = relationship(
        "LeadActivity",
        back_populates="lead",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(LeadActivity.created_at)",
    )
    # batch = relationship("Batch", back_populates="leads", lazy="selectin")


class LeadActivity(Base):
    __tablename__ = "lead_activities"
    __table_args__ = (
        Index("idx_la_lead", "lead_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    lead = relationship("Lead", back_populates="activities")
    user = relationship("User", foreign_keys=[created_by], lazy="selectin")