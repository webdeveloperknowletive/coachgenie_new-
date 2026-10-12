
import uuid
from sqlalchemy import String, Boolean, ForeignKey, text, UniqueConstraint, Index


# import uuid
# from sqlalchemy import String, Boolean, ForeignKey, text, UniqueConstraint, Index
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
# from app.database import Base


# class User(Base):
#     __tablename__ = "users"
#     __table_args__ = (
#         UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
#         Index("idx_users_tenant", "tenant_id"),
#         Index("idx_users_role", "tenant_id", "role"),
#     )

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
#     email: Mapped[str] = mapped_column(String(255), nullable=False)
#     password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
#     role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
#     first_name: Mapped[str] = mapped_column(String(100), nullable=False)
#     last_name: Mapped[str] = mapped_column(String(100), nullable=False)
#     phone: Mapped[str] = mapped_column(String(20), nullable=True)
#     avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
#     is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
#     last_login_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
#     created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
#     updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

#     tenant = relationship("Tenant", back_populates="users")
#     refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


# class RefreshToken(Base):
#     __tablename__ = "refresh_tokens"
#     __table_args__ = (
#         Index("idx_rt_user_tenant", "user_id", "tenant_id"),
#     )

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
#     token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
#     expires_at = mapped_column(TIMESTAMP(timezone=True), nullable=False)
#     revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
#     created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

#     user = relationship("User", back_populates="refresh_tokens")


import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import String, Boolean, ForeignKey, text, UniqueConstraint, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("idx_users_tenant", "tenant_id"),
        Index("idx_users_role", "tenant_id", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    custom_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custom_roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_login_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))

    tenant = relationship("Tenant", back_populates="users")
    custom_role = relationship("CustomRole", back_populates="users", lazy="selectin")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    otp_verifications = relationship("OTPVerification", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("idx_rt_user_tenant", "user_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    user = relationship("User", back_populates="refresh_tokens")


class OTPVerification(Base):
    __tablename__ = "otp_verifications"
    __table_args__ = (
        Index("idx_otp_user", "user_id"),
        Index("idx_otp_email_purpose", "email", "purpose"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Stored as SHA-256 hash, never plain text
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)  # "registration" | "password_reset"
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    user = relationship("User", back_populates="otp_verifications")

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @property
    def is_valid(self) -> bool:

        return not self.is_used and not self.is_expired and self.attempts < 5

        return not self.is_used and not self.is_expired and self.attempts < 5

