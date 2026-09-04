"""
Actions routes - run collection tasks and check status.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.core.database import get_db, RunLog
from app.api.routes_auth import require_auth
from app.services.scheduler_service import scheduler_service

router = APIRouter()


@router.get("/admin")
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """Admin dashboard with statistics."""
    # Get stats
    result = await db.execute(select(RunLog).order_by(desc(RunLog.started_at)).limit(10))
    recent_runs = result.scalars().all()
    
    return request.state.templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "recent_runs": recent_runs,
            "is_scheduler_running": scheduler_service.is_running()
        }
    )


@router.post("/admin/run")
async def run_collection(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """Manually trigger news collection."""
    # Create a run log entry
    run_log = RunLog(status="running", started_at=datetime.utcnow())
    db.add(run_log)
    await db.commit()
    await db.refresh(run_log)
    
    # Run collection in background
    background_tasks.add_task(
        scheduler_service.run_collection_task,
        run_log.id
    )
    
    return {"status": "started", "run_id": run_log.id}


@router.get("/admin/run/{run_id}")
async def get_run_status(
    run_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """Get status of a collection run."""
    result = await db.execute(select(RunLog).where(RunLog.id == run_id))
    run_log = result.scalar_one_or_none()
    
    if not run_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    
    return {
        "id": run_log.id,
        "status": run_log.status,
        "started_at": run_log.started_at.isoformat() if run_log.started_at else None,
        "finished_at": run_log.finished_at.isoformat() if run_log.finished_at else None,
        "news_collected": run_log.news_collected,
        "error_message": run_log.error_message
    }


@router.get("/admin/stats")
async def get_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """Get analytics and statistics."""
    from app.core.database import News, Source
    
    # Total news count
    news_count_result = await db.execute(select(func.count()).select_from(News))
    total_news = news_count_result.scalar()
    
    # News today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count_result = await db.execute(
        select(func.count()).select_from(News).where(News.created_at >= today_start)
    )
    news_today = today_count_result.scalar()
    
    # Duplicates count
    duplicates_result = await db.execute(
        select(func.count()).select_from(News).where(News.is_duplicate == True)
    )
    duplicates = duplicates_result.scalar()
    
    # Sources count
    sources_result = await db.execute(select(func.count()).select_from(Source))
    total_sources = sources_result.scalar()
    
    return {
        "total_news": total_news,
        "news_today": news_today,
        "duplicates": duplicates,
        "total_sources": total_sources
    }
