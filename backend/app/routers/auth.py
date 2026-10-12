import logging

from fastapi import APIRouter, Depends, Request, HTTPException

from app.core.rate_limit import limiter
from app.dependencies import get_tenant, get_current_user, require_roles, DB
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    UserOut,
)
from app.services import auth as auth_service

logger = logging.getLogger("coaching_erp")

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: DB,
    tenant=Depends(get_tenant),
):
    """Public registration — always creates a student account."""
    user = await auth_service.register_user(
        db,
        str(tenant.id),
        body.model_dump(),
    )
    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/register-staff", status_code=201)
@limiter.limit("5/minute")
async def register_staff(
    request: Request,
    body: RegisterRequest,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner")),
):
    """
    Owner-only endpoint to create staff accounts (counselor, tutor, admin).
    FIX BUG-012: previously there was no API way to create non-student users.
    """
    data = body.model_dump()
    # Owner may optionally include 'role' in the request body; defaults to 'counselor'
    allowed_staff_roles = {"counselor", "tutor", "admin"}
    role = data.pop("role", "counselor")
    if role not in allowed_staff_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {sorted(allowed_staff_roles)}",
        )
    user = await auth_service.register_staff_user(
        db,
        str(tenant.id),
        role,
        data,
    )
    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: DB,
):
    raw_subdomain = (
        request.headers.get("x-tenant-subdomain")
        or request.headers.get("X-Tenant-Subdomain")
        or request.headers.get("x-tenant-id")
        or request.headers.get("X-Tenant-Id")
    )

    if raw_subdomain and raw_subdomain.strip():
        tenant = await get_tenant(request, db=db, x_tenant_subdomain=raw_subdomain)
        logger.debug("Login attempt for tenant: %s", tenant.subdomain)
        result = await auth_service.login_user(
            db,
            str(tenant.id),
            body.email,
            body.password,
        )
    else:
        # Platform Super Admin login (no institute subdomain required)
        logger.debug("Platform Super Admin login attempt for email: %s", body.email)
        result = await auth_service.login_platform_super_admin(
            db,
            body.email,
            body.password,
        )

    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": "bearer",
        "user": UserOut(
            id=str(result["user"].id),
            email=result["user"].email,
            first_name=result["user"].first_name,
            last_name=result["user"].last_name,
            role=result["user"].role,
            tenant_id=str(result["user"].tenant_id),
        ),
    }


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    db: DB,
):
    # FIX BUG-013: removed print() that logged full request headers to stdout
    if request.headers.get("x-playwright-fail-refresh") == "1":
        raise HTTPException(
            status_code=401,
            detail="Refresh failed (Playwright)",
        )

    return await auth_service.refresh_tokens(
        db,
        body.refresh_token,
    )


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    db: DB,
):
    await auth_service.logout_user(db, body.refresh_token)
    return {"success": True, "message": "Logged out successfully."}


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id": str(current_user.id),
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role": current_user.role,
        },
    }