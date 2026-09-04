"""
Digest routes - public access.
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional

from app.core.database import get_db, Digest

router = APIRouter()


@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    """Home page with latest digests."""
    result = await db.execute(
        select(Digest).order_by(desc(Digest.generated_at)).limit(10)
    )
    digests = result.scalars().all()
    
    return request.state.templates.TemplateResponse(
        "index.html",
        {"request": request, "digests": digests}
    )


@router.get("/digests")
async def digests_list(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List all digests with pagination."""
    offset = (page - 1) * per_page
    
    result = await db.execute(
        select(Digest).order_by(desc(Digest.generated_at)).offset(offset).limit(per_page)
    )
    digests = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(Digest))
    total = count_result.scalar()
    
    return request.state.templates.TemplateResponse(
        "digests_list.html",
        {
            "request": request,
            "digests": digests,
            "page": page,
            "total_pages": (total + per_page - 1) // per_page
        }
    )


@router.get("/digest/{digest_id}")
async def digest_view(request: Request, digest_id: int, db: AsyncSession = Depends(get_db)):
    """View a specific digest."""
    result = await db.execute(select(Digest).where(Digest.id == digest_id))
    digest = result.scalar_one_or_none()
    
    if not digest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digest not found")
    
    return request.state.templates.TemplateResponse(
        "digest_view.html",
        {"request": request, "digest": digest}
    )
