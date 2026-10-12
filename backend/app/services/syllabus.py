from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from app.models.syllabus import SyllabusItem, SyllabusProgress
from datetime import datetime, timezone


async def get_syllabus(db: AsyncSession, tenant_id: str, batch_id: str) -> list:
    result = await db.execute(
        select(SyllabusItem)
        .options(selectinload(SyllabusItem.progress))
        .where(
            and_(
                SyllabusItem.tenant_id == tenant_id,
                SyllabusItem.batch_id == batch_id,
            )
        )
        .order_by(SyllabusItem.order, SyllabusItem.created_at)
    )
    items = result.scalars().all()

    out = []
    for item in items:
        progress = next((p for p in item.progress if str(p.batch_id) == batch_id), None)
        out.append({
            "id":          str(item.id),
            "title":       item.title,
            "subject":     item.subject,
            "description": item.description,
            "order":       item.order,
            "completed":   progress.completed if progress else False,
            "completed_at": str(progress.completed_at) if progress and progress.completed_at else None,
            "notes":       progress.notes if progress else None,
        })
    return out


async def add_topic(db: AsyncSession, tenant_id: str, batch_id: str, data: dict) -> dict:
    from app.utils.exceptions import ConflictError
    from sqlalchemy import func
    title = (data.get("title") or "").strip()
    if title:
        existing = await db.scalar(
            select(SyllabusItem.id).where(
                and_(
                    SyllabusItem.tenant_id == tenant_id,
                    SyllabusItem.batch_id == batch_id,
                    func.lower(SyllabusItem.title) == title.lower(),
                )
            )
        )
        if existing:
            raise ConflictError(f"A syllabus topic with the title '{title}' already exists for this batch.")

    item = SyllabusItem(
        tenant_id=tenant_id,
        batch_id=batch_id,
        title=title,
        subject=data.get("subject"),
        description=data.get("description"),
        order=data.get("order", 0),
    )
    db.add(item)
    await db.flush()

    # Create progress record
    progress = SyllabusProgress(
        tenant_id=tenant_id,
        batch_id=batch_id,
        item_id=item.id,
        completed=False,
    )
    db.add(progress)
    await db.flush()

    return {
        "id":          str(item.id),
        "title":       item.title,
        "subject":     item.subject,
        "description": item.description,
        "order":       item.order,
        "completed":   False,
        "completed_at": None,
        "notes":       None,
    }


async def toggle_topic(db: AsyncSession, tenant_id: str, batch_id: str, item_id: str, completed: bool, notes: str = None) -> dict:
    result = await db.execute(
        select(SyllabusProgress).where(
            and_(
                SyllabusProgress.tenant_id == tenant_id,
                SyllabusProgress.batch_id == batch_id,
                SyllabusProgress.item_id == item_id,
            )
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        # create if missing
        progress = SyllabusProgress(
            tenant_id=tenant_id,
            batch_id=batch_id,
            item_id=item_id,
            completed=completed,
            completed_at=datetime.now(timezone.utc) if completed else None,
            notes=notes,
        )
        db.add(progress)
    else:
        progress.completed = completed
        progress.completed_at = datetime.now(timezone.utc) if completed else None
        if notes is not None:
            progress.notes = notes

    await db.flush()
    return {"completed": progress.completed}


async def delete_topic(db: AsyncSession, tenant_id: str, batch_id: str, item_id: str):
    result = await db.execute(
        select(SyllabusItem).where(
            and_(
                SyllabusItem.tenant_id == tenant_id,
                SyllabusItem.batch_id == batch_id,
                SyllabusItem.id == item_id,
            )
        )
    )
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.flush()