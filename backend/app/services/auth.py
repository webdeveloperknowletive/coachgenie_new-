import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from app.models.user import User, RefreshToken
from app.utils.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    hash_token, refresh_token_expiry
)
from app.utils.exceptions import UnauthorizedError, ConflictError
from app.schemas import user

logger = logging.getLogger("coaching_erp")


async def register_user(db: AsyncSession, tenant_id: str, data: dict) -> User:
    email_clean = (data["email"] or "").strip().lower()
    phone_clean = (data.get("phone") or "").strip() if data.get("phone") else None
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id

    dup_conds = [func.lower(User.email) == email_clean]
    if phone_clean:
        dup_conds.append(User.phone == phone_clean)

    result = await db.execute(
        select(User).where(
            and_(User.tenant_id == t_uuid, or_(*dup_conds))
        )
    )
    if result.scalar_one_or_none():
        raise ConflictError("A user with this email or phone number is already registered.")

    user = User(
        tenant_id=t_uuid,
        email=email_clean,
        password_hash=hash_password(data["password"]),
        first_name=data["first_name"].strip(),
        last_name=(data.get("last_name") or "").strip(),
        phone=phone_clean,
        role="student",
    )
    db.add(user)
    await db.flush()
    return user


async def register_staff_user(
    db: AsyncSession, tenant_id: str, role: str, data: dict
) -> User:
    """Create a staff user (counselor/tutor/admin) — owner-only action."""
    email_clean = (data["email"] or "").strip().lower()
    phone_clean = (data.get("phone") or "").strip() if data.get("phone") else None
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    
    # Server-side subscription quota verification
    from app.models.tenant import Tenant
    from app.services.entitlement import check_quota
    tenant_obj = await db.get(Tenant, t_uuid)
    if tenant_obj:
        await check_quota(db, tenant_obj, "staff", increment=1)

    dup_conds = [func.lower(User.email) == email_clean]
    if phone_clean:
        dup_conds.append(User.phone == phone_clean)

    result = await db.execute(
        select(User).where(
            and_(User.tenant_id == t_uuid, or_(*dup_conds))
        )
    )
    if result.scalar_one_or_none():
        raise ConflictError("A user with this email or phone number is already registered.")

    staff = User(
        tenant_id=t_uuid,
        email=email_clean,
        password_hash=hash_password(data["password"]),
        first_name=data["first_name"].strip(),
        last_name=(data.get("last_name") or "").strip(),
        phone=phone_clean,
        role=role,
    )
    db.add(staff)
    await db.flush()
    return staff


async def login_user(db: AsyncSession, tenant_id: str, email: str, password: str) -> dict:
    email_clean = (email or "").strip().lower()
    result = await db.execute(
        select(User).where(
            and_(User.tenant_id == uuid.UUID(tenant_id), func.lower(User.email) == email_clean)
        )
    )
    user = result.scalar_one_or_none()

    password_ok = verify_password(password, user.password_hash) if user else False

    if not user or not user.is_active or not password_ok:
        logger.warning(
            f"Login failed for email='{email}' on tenant_id='{tenant_id}'. "
            f"(User found: {user is not None}, Active: {getattr(user, 'is_active', False)}, Password match: {password_ok})"
        )
        raise UnauthorizedError("Invalid email or password for this institute.")

    payload = {
        "sub": str(user.id),
        "tenantId": str(user.tenant_id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "email": user.email,
    }
    access_token = create_access_token(payload)
    raw_refresh, hashed_refresh = create_refresh_token()

    token = RefreshToken(
        user_id=user.id,
        tenant_id=user.tenant_id,
        token_hash=hashed_refresh,
        expires_at=refresh_token_expiry(),
    )
    db.add(token)
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "user": user,
    }


async def login_platform_super_admin(db: AsyncSession, email: str, password: str) -> dict:
    """Platform-level authentication for Super Admin users without requiring an institute subdomain."""
    email_clean = (email or "").strip().lower()
    result = await db.execute(
        select(User).where(
            and_(func.lower(User.email) == email_clean, User.role == "super_admin")
        )
    )
    user = result.scalar_one_or_none()
    password_ok = verify_password(password, user.password_hash) if user else False

    if not user or not user.is_active or not password_ok:
        # Check if the user belongs to a tenant instead
        user_check = (await db.execute(select(User).where(func.lower(User.email) == email_clean))).scalar_one_or_none()
        if user_check:
            raise UnauthorizedError("Institute code is required to sign in to your institute account.")
        raise UnauthorizedError("Invalid email or password.")

    payload = {
        "sub": str(user.id),
        "tenantId": str(user.tenant_id),
        "tenant_id": str(user.tenant_id),
        "role": "super_admin",
        "email": user.email,
    }
    access_token = create_access_token(payload)
    raw_refresh, hashed_refresh = create_refresh_token()

    token = RefreshToken(
        user_id=user.id,
        tenant_id=user.tenant_id,
        token_hash=hashed_refresh,
        expires_at=refresh_token_expiry(),
    )
    db.add(token)
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "user": user,
    }

async def refresh_tokens(db: AsyncSession, raw_refresh: str) -> dict:
    token_hash = hash_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False
            )
        )
    )
    token = result.scalar_one_or_none()

    if not token or token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise UnauthorizedError("Invalid or expired refresh token.")

    user_result = await db.execute(select(User).where(User.id == token.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    # Rotate token
    token.revoked = True
    payload = {
        "sub": str(user.id),

        "tenantId": str(user.tenant_id),


        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "email": user.email
    }
    new_access = create_access_token(payload)
    new_raw, new_hash = create_refresh_token()

    new_token = RefreshToken(
        user_id=user.id,
        tenant_id=user.tenant_id,
        token_hash=new_hash,
        expires_at=refresh_token_expiry(),
    )
    db.add(new_token)
    await db.flush()

    return {"access_token": new_access, "refresh_token": new_raw}


async def logout_user(db: AsyncSession, raw_refresh: str):
    token_hash = hash_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()
    if token:
        token.revoked = True
        await db.flush()
