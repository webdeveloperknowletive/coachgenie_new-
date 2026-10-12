import uuid
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from app.database import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    __table_args__ = (
        Index("idx_auto_rules_tenant_active", "tenant_id", "rule_type", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'attendance_alert', 'fee_overdue', 'late_fee'
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

    tenant = relationship("Tenant")
    updater = relationship("User", foreign_keys=[updated_by])


class AutomationEvent(Base):
    __tablename__ = "automation_events"
    __table_args__ = (
        Index("idx_auto_events_claim", "status", "scheduled_at"),
        Index("idx_auto_events_tenant", "tenant_id", "created_at"),
        Index("idx_auto_events_lease", "status", "lease_expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")  # PENDING, CLAIMED, RUNNING, SUCCEEDED, FAILED, RETRY_WAIT, CANCELLED
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    scheduled_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False)
    claimed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    claimed_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    lease_expires_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    tenant = relationship("Tenant")


class AutomationExecution(Base):
    __tablename__ = "automation_executions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_tenant_idempotency"),
        Index("idx_auto_exec_lookup", "tenant_id", "idempotency_key"),
        Index("idx_auto_exec_tenant_time", "tenant_id", "executed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCEEDED")  # SUCCEEDED, FAILED, SKIPPED
    details: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    executed_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    tenant = relationship("Tenant")


class WebPushSubscription(Base):
    __tablename__ = "web_push_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", name="uq_user_push_endpoint"),
        Index("idx_webpush_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False)
    auth_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    tenant = relationship("Tenant")
    user = relationship("User")
