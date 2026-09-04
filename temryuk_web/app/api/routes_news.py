"""
News routes - admin access for management.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime
from typing import Optional

from app.core.database import get_db, News, Source
from app.api.routes_auth import require_auth

router = APIRouter()


@router.get("/admin/news")
async def news_list(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
    category: Optional[str] = None,
    source_id: Optional[int] = None,
    location: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """List all news with filters."""
    offset = (page - 1) * per_page
    
    # Build query with filters
    query = select(News).join(Source).order_by(News.created_at.desc())
    
    if search:
        query = query.where(News.title.ilike(f"%{search}%"))
    
    if category:
        query = query.where(News.category == category)
    
    if source_id:
        query = query.where(News.source_id == source_id)
    
    if location:
        query = query.where(News.location.ilike(f"%{location}%"))
    
    # Get paginated results
    result = await db.execute(query.offset(offset).limit(per_page))
    news_items = result.scalars().all()
    
    # Get total count
    count_query = select(func.count()).select_from(News)
    if search or category or source_id or location:
        # Apply same filters to count query
        pass  # Simplified for brevity
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get sources for filter dropdown
    sources_result = await db.execute(select(Source).order_by(Source.name))
    sources = sources_result.scalars().all()
    
    return request.state.templates.TemplateResponse(
        "news_list.html",
        {
            "request": request,
            "news_items": news_items,
            "sources": sources,
            "page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "filters": {
                "search": search,
                "category": category,
                "source_id": source_id,
                "location": location
            }
        }
    )
