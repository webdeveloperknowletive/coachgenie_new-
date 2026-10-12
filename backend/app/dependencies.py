# from fastapi import Depends, Header, Request
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, and_
# from typing import Annotated

# from app.database import get_db
# from app.models.tenant import Tenant
# from app.models.user import User
# from app.utils.security import decode_access_token
# from app.utils.exceptions import UnauthorizedError, ForbiddenError, TenantNotFoundError
# import uuid


# async def get_tenant(
#     db: AsyncSession = Depends(get_db),

#     x_tenant_subdomain: str | None = Header(default=None),  # ← matches "X-Tenant-Subdomain"
#     x_tenant_id: str | None = Header(default=None),         # ← fallback for old header

# ) -> Tenant:
#     """
#     Accepts X-Tenant-Subdomain (primary) or X-Tenant-Id (fallback).
#     Automatically detects UUID vs subdomain string.
#     """

#     # prefer X-Tenant-Subdomain, fall back to X-Tenant-Id
#     raw = x_tenant_subdomain or x_tenant_id

#     if not raw:
#         raise TenantNotFoundError("X-Tenant-Subdomain header is missing")


#     # detect if UUID → query by id, otherwise query by subdomain


#     # detect if UUID ? query by id, otherwise query by subdomain
#     try:
#         uuid.UUID(raw)
#         query = select(Tenant).where(Tenant.id == raw)
#     except ValueError:
#         query = select(Tenant).where(Tenant.subdomain == raw)

#     result = await db.execute(query)
#     tenant = result.scalar_one_or_none()

#     if not tenant or not tenant.is_active:
#         raise TenantNotFoundError(f"Tenant '{raw}' not found or inactive")

#     return tenant


# # async def get_current_user(
# #     request: Request,
# #     db: AsyncSession = Depends(get_db),
# #     tenant: Tenant = Depends(get_tenant),
# # ) -> User:
# #     auth_header = request.headers.get("Authorization", "")
# #     if not auth_header.startswith("Bearer "):
# #         raise UnauthorizedError("No token provided.")

# #     token = auth_header.split(" ")[1]
# #     payload = decode_access_token(token)

# #     result = await db.execute(
# #         select(User).where(
# #             and_(
# #                 User.id == uuid.UUID(payload["sub"]),
# #                 User.tenant_id == tenant.id,
# #             )
# #         )
# #     )
# #     user = result.scalar_one_or_none()
# #     if not user or not user.is_active:
# #         raise UnauthorizedError("User not found or inactive.")
# #     return user
# async def get_current_user(
#     request: Request,
#     db: AsyncSession = Depends(get_db),
#     tenant: Tenant = Depends(get_tenant),
# ) -> User:
#     auth_header = request.headers.get("Authorization", "")
#     if not auth_header.startswith("Bearer "):
#         raise UnauthorizedError("No token provided.")

#     token = auth_header.split(" ")[1]
#     payload = decode_access_token(token)


#     # ✅ handle both camelCase and snake_case
#     tenant_id = payload.get("tenant_id") or payload.get("tenantId")



#     result = await db.execute(
#         select(User).where(
#             and_(
#                 User.id == uuid.UUID(payload["sub"]),
#                 User.tenant_id == tenant.id,
#             )
#         )
#     )
#     user = result.scalar_one_or_none()
#     if not user or not user.is_active:
#         raise UnauthorizedError("User not found or inactive.")
#     return user


# def require_roles(*roles: str):
#     async def checker(
#         current_user: User = Depends(get_current_user),
#     ) -> User:
#         if current_user.role not in roles:
#             raise ForbiddenError(
#                 f"Required roles: {roles}. Your role: {current_user.role}"
#             )
#         return current_user
#     return checker



# # ── Simple type aliases ───────────────────────────────────────
# DB            = Annotated[AsyncSession, Depends(get_db)]
# CurrentUser   = Annotated[User,         Depends(get_current_user)]
# CurrentTenant = Annotated[Tenant,       Depends(get_tenant)]


# # -- Simple type aliases ---------------------------------------
# -- Simple type aliases ---------------------------------------
# DB            = Annotated[AsyncSession, Depends(get_db)]
# CurrentUser   = Annotated[User,         Depends(get_current_user)]
# CurrentTenant = Annotated[Tenant,       Depends(get_tenant)]



import logging
import uuid

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Annotated

from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.utils.security import decode_access_token
from app.utils.exceptions import (
    UnauthorizedError,
    ForbiddenError,
    TenantNotFoundError,
)

logger = logging.getLogger("coaching_erp")


async def get_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_tenant_subdomain: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
) -> Tenant:
    raw = x_tenant_subdomain or x_tenant_id

    if not raw or not raw.strip():
        # Check if auth token has tenant_id before failing
        auth_hdr = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            try:
                token = auth_hdr.split(" ")[1]
                payload = decode_access_token(token)
                tid = payload.get("tenant_id") or payload.get("tenantId")
                if tid:
                    raw = str(tid)
            except Exception:
                pass

        if not raw or not raw.strip():
            raise TenantNotFoundError("Institute code (X-Tenant-Subdomain) is required.")

    sub_clean = raw.strip().lower()

    try:
        uuid_val = uuid.UUID(sub_clean)
        stmt = select(Tenant).where(Tenant.id == uuid_val)
    except ValueError:
        stmt = select(Tenant).where(func.lower(Tenant.subdomain) == sub_clean)

    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    # Only provision demo if the user specifically requested "demo"
    if not tenant and sub_clean == "demo":
        try:
            from app.services.tenant_provisioning import ensure_demo_tenant
            await ensure_demo_tenant()
            stmt_demo = select(Tenant).where(Tenant.subdomain == "demo")
            tenant = (await db.execute(stmt_demo)).scalar_one_or_none()
        except Exception as err:
            logger.warning(f"Demo tenant on-demand provisioning note: {err}")

    if not tenant:
        logger.warning(f"Tenant resolution failed for institute code: '{raw}'")
        raise TenantNotFoundError(f"Institute code '{raw}' is invalid or does not exist.")

    if not tenant.is_active:
        logger.warning(f"Suspended tenant access attempt: '{raw}'")
        raise ForbiddenError("Institute workspace is currently suspended. Please contact platform support.")

    return tenant


from fastapi.security import HTTPBearer

security_scheme = HTTPBearer(auto_error=False)


from sqlalchemy.orm import selectinload
from app.services.rbac import has_permission


async def get_current_user(
    request: Request,
    token_obj = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
) -> User:

    auth_header = request.headers.get("Authorization", "")
    if not auth_header and token_obj:
        auth_header = f"Bearer {token_obj.credentials}"

    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("No token provided.")

    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)

    # Diagnostic Impersonation Security Enforcement
    is_diag = bool(payload.get("is_diagnostic", False))
    request.state.is_diagnostic = is_diag

    if is_diag:
        # 1. Strictly enforce READ-ONLY mode on all mutation HTTP verbs
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            raise ForbiddenError(
                "Diagnostic Mode Restriction: Impersonation sessions are strictly read-only for troubleshooting. Data modifications, creations, and deletions are prohibited."
            )
        # 2. Prevent token refresh or diagnostic token re-issuance
        if request.url.path.endswith("/auth/refresh") or request.url.path.endswith("/auth/change-password"):
            raise ForbiddenError("Diagnostic sessions cannot refresh tokens or alter user credentials.")

    result = await db.execute(
        select(User)
        .options(selectinload(User.custom_role))
        .where(
            and_(
                User.id == uuid.UUID(payload["sub"]),
                User.tenant_id == tenant.id,
            )
        )
    )

    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    return user


from app.services.rbac import has_permission, LEGACY_ROLE_PERMISSIONS


def require_roles(*roles: str):
    allowed = {r.strip().lower() for r in roles}
    async def checker(current_user: User = Depends(get_current_user)):
        user_role = (current_user.role or "").strip().lower()
        if user_role in allowed or user_role in {"owner", "super_admin"}:
            return current_user

        # If user has an active custom role, verify if it grants access to the module/role capabilities
        if getattr(current_user, "custom_role", None) and current_user.custom_role and current_user.custom_role.is_active:
            user_perms = set(current_user.custom_role.permissions or [])
            if "*.*" in user_perms:
                return current_user
            for r in allowed:
                r_perms = LEGACY_ROLE_PERMISSIONS.get(r, set())
                if any(p in user_perms or f"{p.split('.')[0]}.*" in user_perms for p in r_perms):
                    return current_user

        raise ForbiddenError(
            f"Required roles: {roles}. Your role: {current_user.role}"
        )

    return checker


def require_permission(resource: str, action: str):
    """
    Fine-grained, server-side dynamic RBAC dependency.
    Evaluates resource.action against user's custom role and built-in role permissions.
    """
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, resource, action):
            raise ForbiddenError(
                f"Access Denied: You do not have permission to perform '{action}' on '{resource}'."
            )
        return current_user

    return checker


async def get_current_super_admin(
    request: Request,
    token_obj = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Super Admin authentication dependency enforcing role validation and diagnostic exclusion."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header and token_obj:
        auth_header = f"Bearer {token_obj.credentials}"

    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("No token provided.")

    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)

    if payload.get("is_diagnostic"):
        raise ForbiddenError("Diagnostic tokens are restricted and cannot access platform administration.")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload.")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    role_norm = (user.role or "").strip().lower()
    if role_norm not in {"super_admin", "superadmin"}:
        raise ForbiddenError("Access Denied: Super Admin privileges required.")

    return user


def require_feature_entitlement(feature_name: str):
    """Verifies that the tenant's subscription plan entitles them to use a specific feature."""
    async def checker(tenant: Tenant = Depends(get_tenant)) -> Tenant:
        from app.services.entitlement import is_feature_enabled
        if not is_feature_enabled(tenant, feature_name):
            raise ForbiddenError(
                f"Feature '{feature_name}' is not enabled for your subscription plan. Please upgrade your plan."
            )
        return tenant

    return checker


DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_tenant)]
SuperAdminUser = Annotated[User, Depends(get_current_super_admin)]