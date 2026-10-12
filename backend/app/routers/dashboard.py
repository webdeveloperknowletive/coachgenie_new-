from fastapi import APIRouter, Depends
from app.dependencies import get_tenant, get_current_user, DB, require_roles
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
async def get_dashboard(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(get_current_user),
):
    role = current_user.role

    if role == "owner":
        data = await dashboard_service.get_owner_dashboard(db, str(tenant.id))
    elif role == "tutor":
        data = await dashboard_service.get_tutor_dashboard(
            db, str(tenant.id), str(current_user.id)
        )
    elif role == "counselor":
        data = await dashboard_service.get_counselor_dashboard(db, str(tenant.id))
    elif role == "student":
        # Get student record linked to this user
        from sqlalchemy import select, and_
        from app.models.student import Student
        result = await db.execute(
            select(Student).where(
                and_(
                    Student.tenant_id == tenant.id,
                    Student.user_id == current_user.id
                )
            )
        )
        student = result.scalar_one_or_none()
        if not student:
            return {"success": True, "data": {"message": "No student record linked to this account."}}
        data = await dashboard_service.get_student_dashboard(
            db, str(tenant.id), str(student.id)
        )
    elif role == "parent":
        from sqlalchemy import select, and_, or_
        from app.models.student import Student
        result = await db.execute(
            select(Student).where(
                and_(
                    Student.tenant_id == tenant.id,
                    or_(
                        Student.parent_user_id == current_user.id,
                        Student.parent_email == current_user.email,
                    ),
                )
            )
        )
        students = result.scalars().all()
        if not students:
            return {"success": True, "data": {"message": "No student linked to this parent account."}}
        # Aggregate dashboard data for all linked children
        all_data = []
        for student in students:
            child_data = await dashboard_service.get_student_dashboard(
                db, str(tenant.id), str(student.id)
            )
            all_data.append({
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}".strip(),
                "dashboard": child_data,
            })
        data = {"children": all_data}
    else:
        data = {"message": "No dashboard available for this role."}

    return {"success": True, "role": role, "data": data}


@router.get("/owner")
async def owner_dashboard(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner")),
):
    data = await dashboard_service.get_owner_dashboard(db, str(tenant.id))
    return {"success": True, "data": data}


@router.get("/counselor")
async def counselor_dashboard(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("counselor")),
):
    data = await dashboard_service.get_counselor_dashboard(db, str(tenant.id))
    return {"success": True, "data": data}


@router.get("/tutor")
async def tutor_dashboard(
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(require_roles("owner", "tutor")),
):
    data = await dashboard_service.get_tutor_dashboard(
        db, str(tenant.id), str(current_user.id)
    )
    return {"success": True, "data": data}


@router.get("/student/{student_id}")
async def student_dashboard(
    student_id: str,
    db: DB,
    tenant=Depends(get_tenant),
    current_user=Depends(get_current_user),
):
    """
    FIX BUG-010: Added role-based ownership check.
    - Owners / counselors / tutors → can access any student's dashboard.
    - Students → can only access their own dashboard.
    - Parents → can only access their linked student's dashboard.
    """
    from fastapi import HTTPException
    from sqlalchemy import select, and_
    from app.models.student import Student

    if current_user.role in ("owner", "counselor", "tutor"):
        # Staff roles: unrestricted access
        pass
    elif current_user.role == "student":
        result = await db.execute(
            select(Student).where(
                and_(
                    Student.tenant_id == tenant.id,
                    Student.user_id == current_user.id,
                )
            )
        )
        linked = result.scalar_one_or_none()
        if not linked or str(linked.id) != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == "parent":
        result = await db.execute(
            select(Student).where(
                and_(
                    Student.tenant_id == tenant.id,
                    Student.parent_email == current_user.email,
                )
            )
        )
        linked = result.scalar_one_or_none()
        if not linked or str(linked.id) != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        raise HTTPException(status_code=403, detail="Access denied")

    data = await dashboard_service.get_student_dashboard(
        db, str(tenant.id), student_id
    )
    return {"success": True, "data": data}
