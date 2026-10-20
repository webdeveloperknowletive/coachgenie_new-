import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine
from app.scheduler import start_scheduler, scheduler
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

import app.models  # noqa: F401

from app.routers import (
    auth, tenants, leads, students, admissions,
    batches, attendance, exams, fees, notifications, ai,
    parents, tutors, admins, growth_cards, auth_extended,
    dashboard, syllabus, inbox_notification, roles, audit,
    platform, automation,
)
from app.routers.ai_reports import router as ai_reports_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coaching_erp")


from app.database import engine, Base
import app.models  # ensure models are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created.")

    try:
        from app.services.tenant_provisioning import ensure_demo_tenant
        await ensure_demo_tenant()
    except Exception as e:
        logger.warning(f"Demo tenant initialization note: {e}")

    import os
    if os.getenv("ALLOW_SEED", "false").lower() in ("true", "1"):
        try:
            from seed import seed
            await seed()
        except Exception as e:
            logger.info(f"Seed note: {e}")

    start_scheduler()
    yield
    scheduler.shutdown()
    await engine.dispose()


tags_metadata = [
    {"name": "Auth", "description": "Authentication, JWT tokens, session management, and password reset workflows."},
    {"name": "Tenants", "description": "Multi-tenant coaching institute management and subdomain provisioning."},
    {"name": "Leads", "description": "Sales CRM pipeline, prospective student lead management, and conversion tracking."},
    {"name": "Admissions", "description": "Student registration forms, document verification, and admission approval."},
    {"name": "Students", "description": "Enrolled student profiles, academic rosters, and emergency contact details."},
    {"name": "Batches", "description": "Course batch scheduling, faculty allocations, and class sessions."},
    {"name": "Attendance", "description": "Daily student attendance marking, absent alerts, and historical percentage reports."},
    {"name": "Exams", "description": "Examination creation, student mark entry, class rankings, and report cards."},
    {"name": "Fees", "description": "Course fee structures, student invoices, partial payment settlements, and PDF receipts."},
    {"name": "Growth Cards", "description": "360-degree student performance evaluations, soft skills, and faculty remarks."},
    {"name": "AI", "description": "Context-aware Groq LLaMA 3 study assistance and interactive learning copilot."},
    {"name": "Notifications", "description": "System alerts, payment due reminders, and inbox notifications."},
    {"name": "Dashboard", "description": "Executive dashboard statistics, revenue metrics, and operational KPIs."},
]

app = FastAPI(
    title=f"{settings.APP_NAME} Multi-Tenant REST API",
    description="""
### CoachGenie Enterprise ERP API Specification

Welcome to the official API documentation for **CoachGenie Phase 1**.

#### 🔑 Authentication & Headers
* **Bearer Token**: `Authorization: Bearer <access_token>`
* **Tenant Isolation**: `X-Tenant-Id: <tenant_uuid>` or `X-Tenant-Subdomain: <subdomain>`

#### 📚 Documentation Endpoints
* **Swagger UI**: `/docs`
* **ReDoc Interface**: `/redoc`
* **OpenAPI Schema**: `/openapi.json`
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database execution exception: %s", exc, exc_info=True)
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "A database operation error occurred."},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback

    traceback.print_exc()
    logger.error("Unhandled exception: %s — %s", type(exc).__name__, exc)

    if settings.DEBUG:
        detail = {"message": str(exc), "type": type(exc).__name__}
    else:
        detail = {"message": "An internal server error occurred. Please try again later."}

    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"success": False, **detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )

@app.get("/health")
async def health():
    """Fast liveness probe."""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/health/ready")
async def health_ready():
    """Deep readiness probe verifying database connectivity safely without exposing internals."""
    from sqlalchemy import text
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unready"})


PREFIX = "/api/v1"
app.include_router(tenants.router,            prefix=PREFIX)
app.include_router(auth.router,               prefix=PREFIX)
app.include_router(leads.router,              prefix=PREFIX)
app.include_router(students.router,           prefix=PREFIX)
app.include_router(admissions.router,         prefix=PREFIX)
app.include_router(batches.router,            prefix=PREFIX)
app.include_router(attendance.router,         prefix=PREFIX)
app.include_router(exams.router,              prefix=PREFIX)
app.include_router(fees.router,               prefix=PREFIX)
app.include_router(notifications.router,      prefix=PREFIX)
app.include_router(ai.router,                 prefix=PREFIX)
app.include_router(growth_cards.router,       prefix=PREFIX)
app.include_router(auth_extended.router,      prefix=PREFIX)
app.include_router(dashboard.router,          prefix=PREFIX)
app.include_router(ai_reports_router,         prefix=PREFIX)
app.include_router(syllabus.router,           prefix=PREFIX)
app.include_router(parents.router,            prefix=PREFIX)
app.include_router(tutors.router,             prefix=PREFIX)
app.include_router(admins.router,             prefix=PREFIX)
app.include_router(inbox_notification.router, prefix=PREFIX)
app.include_router(roles.router,              prefix=PREFIX)
app.include_router(audit.router,              prefix=PREFIX)
app.include_router(platform.router,           prefix=PREFIX)
app.include_router(automation.router,         prefix=PREFIX)
app.include_router(automation.push_router,    prefix=PREFIX)