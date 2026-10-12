import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from app.models.lead import Lead, LeadActivity
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate


async def get_funnel(db: AsyncSession, tenant_id: str) -> list:
    from app.models.student import Student

    result = await db.execute(
        select(
            Lead.status,
            func.count(Lead.id).label("count")
        )
        .where(Lead.tenant_id == tenant_id)
        .group_by(Lead.status)
    )

    rows = result.all()

    raw_counts = {
        (row.status or "").lower(): row.count
        for row in rows
    }

    # Total active enrolled students in institute
    active_students_count = (await db.execute(
        select(func.count(Student.id))
        .where(and_(Student.tenant_id == tenant_id, Student.is_active == True))
    )).scalar() or 0

    enrolled_count = max(
        raw_counts.get("enrolled", 0) + raw_counts.get("converted", 0),
        active_students_count
    )

    enquiries_count = raw_counts.get("new", 0) + raw_counts.get("enquiry", 0) + raw_counts.get("enquiries", 0)
    contacted_count = raw_counts.get("contacted", 0) + raw_counts.get("demo_scheduled", 0)
    trial_count = raw_counts.get("interested", 0) + raw_counts.get("demo_done", 0) + raw_counts.get("negotiation", 0)
    lost_count = raw_counts.get("lost", 0)

    return [
        {"stage": "Enquiries", "count": enquiries_count},
        {"stage": "Contacted", "count": contacted_count},
        {"stage": "Trial", "count": trial_count},
        {"stage": "Enrolled", "count": enrolled_count},
        {"stage": "Lost", "count": lost_count},
    ]


# ── helper: attach batch_name to a lead object ────────────────────────────────
async def _attach_batch_name(db: AsyncSession, lead: Lead) -> Lead:
    """Fetch batch name and attach it as a non-mapped attribute."""
    if lead.batch_id:
        from app.models.batch import Batch
        batch = await db.get(Batch, lead.batch_id)
        lead.__dict__["batch_name"] = batch.name if batch else None
    else:
        lead.__dict__["batch_name"] = None
    return lead


async def get_leads(
    db: AsyncSession,
    tenant_id: str,
    page: int,
    limit: int,
    status: str | None,
    search: str | None,
    batch_id: str | None = None,       # ← NEW
) -> dict:
    conditions = [Lead.tenant_id == tenant_id]

    if status:
        conditions.append(Lead.status == status)

    if search:
        conditions.append(
            or_(
                Lead.full_name.ilike(f"%{search}%"),
                Lead.phone.ilike(f"%{search}%"),
            )
        )

    if batch_id:                                           # ← NEW
        conditions.append(Lead.batch_id == batch_id)      # ← NEW

    total = (await db.execute(
        select(func.count()).select_from(Lead).where(and_(*conditions))
    )).scalar()

    result = await db.execute(
        select(Lead).where(and_(*conditions))
        .order_by(Lead.created_at.desc())
        .offset((page - 1) * limit).limit(limit)
    )
    leads = result.scalars().all()

    # ── attach batch_name to each lead ────────────────────────────────────────
    for lead in leads:
        await _attach_batch_name(db, lead)

    return paginate(leads, total, page, limit)


async def get_lead(db: AsyncSession, tenant_id: str, lead_id: str) -> Lead:
    import uuid
    try:
        uuid_obj = uuid.UUID(str(lead_id))
        tenant_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    except (ValueError, TypeError):
        raise NotFoundError("Lead")

    result = await db.execute(
        select(Lead).where(and_(Lead.id == uuid_obj, Lead.tenant_id == tenant_uuid))
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise NotFoundError("Lead")

    # ── attach batch_name ─────────────────────────────────────────────────────
    await _attach_batch_name(db, lead)

    return lead


async def create_lead(db: AsyncSession, tenant_id: str, data: dict) -> Lead:
    import uuid
    from app.utils.exceptions import ConflictError
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id

    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip().lower()

    dup_conditions = []
    if phone:
        dup_conditions.append(Lead.phone == phone)
    if email:
        dup_conditions.append(func.lower(Lead.email) == email)

    if dup_conditions:
        existing = await db.scalar(
            select(Lead.id).where(
                and_(
                    Lead.tenant_id == t_uuid,
                    or_(*dup_conditions)
                )
            )
        )
        if existing:
            raise ConflictError("A lead with this phone number or email already exists in this institute.")

    lead = Lead(tenant_id=t_uuid, **data)
    db.add(lead)
    await db.flush()

    # ── attach batch_name ─────────────────────────────────────────────────────
    await _attach_batch_name(db, lead)

    return lead


async def update_lead(db: AsyncSession, tenant_id: str, lead_id: str, data: dict) -> Lead:
    import uuid
    from app.utils.exceptions import ConflictError
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    lead = await get_lead(db, tenant_id, lead_id)

    new_phone = (data.get("phone") or "").strip() if "phone" in data and data["phone"] is not None else None
    new_email = (data.get("email") or "").strip().lower() if "email" in data and data["email"] is not None else None

    dup_conditions = []
    if new_phone and new_phone != lead.phone:
        dup_conditions.append(Lead.phone == new_phone)
    if new_email and new_email != (lead.email or "").lower():
        dup_conditions.append(func.lower(Lead.email) == new_email)

    if dup_conditions:
        existing = await db.scalar(
            select(Lead.id).where(
                and_(
                    Lead.tenant_id == t_uuid,
                    Lead.id != lead.id,
                    or_(*dup_conditions)
                )
            )
        )
        if existing:
            raise ConflictError("Another lead with this phone number or email already exists in this institute.")

    for key, value in data.items():
        if value is not None:
            setattr(lead, key, value)
    await db.flush()

    # ── attach batch_name ─────────────────────────────────────────────────────
    await _attach_batch_name(db, lead)

    return lead


async def delete_lead(db: AsyncSession, tenant_id: str, lead_id: str):
    lead = await get_lead(db, tenant_id, lead_id)
    await db.delete(lead)
    await db.flush()


async def add_activity(db: AsyncSession, tenant_id: str, lead_id: str,
                       user_id: str | None, data: dict) -> LeadActivity:
    import uuid
    tenant_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    lead_uuid = uuid.UUID(str(lead_id)) if isinstance(lead_id, (str, uuid.UUID)) else lead_id
    user_uuid = None
    if user_id:
        try:
            user_uuid = uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            user_uuid = None

    act_type = str(data.get("type") or "NOTE").upper()
    act_desc = str(data.get("description") or data.get("content") or "").strip()

    activity = LeadActivity(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        lead_id=lead_uuid,
        created_by=user_uuid,
        type=act_type,
        description=act_desc,
    )
    db.add(activity)
    await db.flush()
    return activity


DEFAULT_CRM_PIPELINE = {
    "stages": [
        {"id": "new", "label": "New Inquiry", "order": 1, "is_system": True},
        {"id": "contacted", "label": "Contacted", "order": 2, "is_system": False},
        {"id": "counselling", "label": "Counseling Session", "order": 3, "is_system": False},
        {"id": "demo_scheduled", "label": "Demo Class Scheduled", "order": 4, "is_system": False},
        {"id": "negotiation", "label": "Fee Negotiation", "order": 5, "is_system": False},
        {"id": "converted", "label": "Converted / Enrolled", "order": 6, "is_system": True},
        {"id": "lost", "label": "Lost / Dropped", "order": 7, "is_system": True},
    ],
    "required_documents": [
        {"id": "photo", "name": "Student Passport Photo", "mandatory": True},
        {"id": "aadhaar", "name": "Identity Proof (Aadhaar/ID)", "mandatory": False},
        {"id": "marksheet", "name": "Previous Year Marksheet", "mandatory": False},
    ],
}


async def get_crm_pipeline(db: AsyncSession, tenant_id: str | uuid.UUID) -> dict:
    from app.models.tenant import Tenant
    import uuid
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    tenant = await db.get(Tenant, t_uuid)
    if not tenant:
        raise NotFoundError("Tenant")
    settings = tenant.settings or {}
    return settings.get("crm_pipeline") or DEFAULT_CRM_PIPELINE


async def update_crm_pipeline(
    db: AsyncSession,
    tenant_id: str | uuid.UUID,
    pipeline_data: dict,
    actor_id: str | uuid.UUID | None = None,
    ip_address: str | None = None,
) -> dict:
    from app.models.tenant import Tenant
    from app.services.audit import log_audit_event
    from app.utils.exceptions import BadRequestError
    import uuid

    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    tenant = await db.get(Tenant, t_uuid)
    if not tenant:
        raise NotFoundError("Tenant")

    current_pipeline = await get_crm_pipeline(db, t_uuid)
    old_stage_ids = {s["id"] for s in current_pipeline.get("stages", [])}
    new_stage_ids = {s["id"] for s in pipeline_data.get("stages", [])}

    # Deletion guard: Check if removed stages are referenced by existing leads
    removed_stage_ids = old_stage_ids - new_stage_ids
    for removed_id in removed_stage_ids:
        lead_count = await db.scalar(
            select(func.count(Lead.id)).where(
                and_(Lead.tenant_id == t_uuid, Lead.status == removed_id)
            )
        ) or 0
        if lead_count > 0:
            raise BadRequestError(
                f"Cannot delete stage '{removed_id}' because {lead_count} lead(s) are currently assigned to it. Please reassign them first."
            )

    settings = dict(tenant.settings or {})
    settings["crm_pipeline"] = pipeline_data
    tenant.settings = settings
    await db.flush()

    await log_audit_event(
        db,
        tenant_id=t_uuid,
        actor_id=actor_id,
        action="UPDATE_CRM_PIPELINE",
        entity_type="crm_pipeline",
        entity_id=str(t_uuid),
        ip_address=ip_address,
        metadata={"stages_count": len(pipeline_data.get("stages", []))},
    )

    return settings["crm_pipeline"]


async def get_activities(db: AsyncSession, tenant_id: str, lead_id: str) -> list:
    import uuid
    try:
        lead_uuid = uuid.UUID(str(lead_id))
        tenant_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    except (ValueError, TypeError):
        return []

    result = await db.execute(
        select(LeadActivity).where(
            and_(
                LeadActivity.lead_id == lead_uuid,
                LeadActivity.tenant_id == tenant_uuid,
            )
        ).order_by(LeadActivity.created_at.desc())
    )
    return result.scalars().all()