import uuid
from sqlalchemy import String, Boolean, Text, ForeignKey, text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from app.database import Base


class CustomRole(Base):
    __tablename__ = "custom_roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_custom_roles_tenant_name"),
        Index("idx_custom_roles_tenant", "tenant_id"),
        Index("idx_custom_roles_active", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Permissions stored as list of string identifiers, e.g. ["leads.view", "fees.create", "attendance.edit"]
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    users = relationship("User", back_populates="custom_role")
