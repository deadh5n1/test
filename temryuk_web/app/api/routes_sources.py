"""
Sources management routes - admin only.
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from app.core.database import get_db, Source
from app.api.routes_auth import require_auth

router = APIRouter()


@router.get("/admin/sources")
async def sources_list(request: Request, db: AsyncSession = Depends(get_db), _=Depends(require_auth)):
    """List all sources."""
    result = await db.execute(select(Source).order_by(Source.name))
    sources = result.scalars().all()
    
    return request.state.templates.TemplateResponse(
        "sources.html",
        {"request": request, "sources": sources}
    )


@router.post("/admin/sources/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """Toggle source active/inactive."""
    await db.execute(
        update(Source)
        .where(Source.id == source_id)
        .values(is_active=not Source.is_active)
    )
    await db.commit()
    
    return {"status": "success"}


@router.get("/admin/sources/{source_id}/check")
async def check_source(
    source_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """Check source availability."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    
    # Simple availability check (could be enhanced with actual HTTP request)
    is_available = True  # Placeholder
    
    return {
        "source_id": source_id,
        "name": source.name,
        "is_available": is_available,
        "url": source.url
    }
