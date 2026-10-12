from fastapi import APIRouter, Depends, Query, HTTPException
from app.dependencies import get_tenant, require_roles, DB
from app.services import parent as parent_service
from app.models.student import Student

router = APIRouter(prefix="/parents", tags=["Parents"])


@router.get("/children")
async def list_children(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("parent", "owner", "admin")),
):
    """
    Returns the list of authorized children for the authenticated parent.
    """
    children = await parent_service.resolve_authorized_children(db, str(tenant.id), current_user)
    return {
        "success": True,
        "data": [
            {
                "id": str(c.id),
                "first_name": c.first_name,
                "last_name": c.last_name,
                "enrollment_no": c.enrollment_no,
                "current_class": c.current_class,
                "photo_url": c.photo_url,
                "school_name": c.school_name,
                "target_exam": c.target_exam,
            }
            for c in children
        ],
    }


@router.get("/portal/dashboard")
async def parent_dashboard(
    db: DB,
    student_id: str | None = Query(None, description="Target child ID"),
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("parent")),
):
    """
    Aggregates academic, attendance, fee, and notification overview for the requested child.
    Server verifies parent-child authorization; never trusts client ID blindly.
    """
    data = await parent_service.get_parent_portal_dashboard(
        db, str(tenant.id), current_user, requested_student_id=student_id
    )
    return {"success": True, "data": data}