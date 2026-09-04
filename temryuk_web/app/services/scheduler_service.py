"""
Scheduler service for background tasks.
Uses APScheduler to run periodic news collection.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import SCHEDULER_INTERVAL_HOURS
from app.core.database import async_session_maker, RunLog, Source
from app.services.news_service import NewsService
from app.services.digest_service import DigestService


class SchedulerService:
    """Service for managing scheduled tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    def start(self):
        """Start the scheduler."""
        if not self._is_running:
            # Add job for periodic news collection
            self.scheduler.add_job(
                self._run_scheduled_collection,
                trigger=IntervalTrigger(hours=SCHEDULER_INTERVAL_HOURS),
                id='news_collection',
                replace_existing=True
            )
            
            self.scheduler.start()
            self._is_running = True
    
    def stop(self):
        """Stop the scheduler."""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running
    
    async def _run_scheduled_collection(self):
        """Run scheduled news collection task."""
        async with async_session_maker() as db:
            # Create run log
            run_log = RunLog(
                status="running",
                started_at=datetime.utcnow()
            )
            db.add(run_log)
            await db.commit()
            await db.refresh(run_log)
            
            try:
                # Run collection
                news_service = NewsService(db)
                result = await news_service.collect_news()
                
                # Generate digest
                digest_service = DigestService(db)
                await digest_service.generate_digest()
                
                # Update run log
                await db.execute(
                    update(RunLog)
                    .where(RunLog.id == run_log.id)
                    .values(
                        status="success",
                        finished_at=datetime.utcnow(),
                        news_collected=result.news_collected
                    )
                )
                
            except Exception as e:
                # Update run log with error
                await db.execute(
                    update(RunLog)
                    .where(RunLog.id == run_log.id)
                    .values(
                        status="error",
                        finished_at=datetime.utcnow(),
                        error_message=str(e)
                    )
                )
            
            await db.commit()
    
    async def run_collection_task(self, run_log_id: int):
        """
        Run collection task manually (for admin-triggered runs).
        
        Args:
            run_log_id: ID of the run log entry
        """
        async with async_session_maker() as db:
            try:
                # Run collection
                news_service = NewsService(db)
                result = await news_service.collect_news()
                
                # Generate digest
                digest_service = DigestService(db)
                await digest_service.generate_digest()
                
                # Update run log
                await db.execute(
                    update(RunLog)
                    .where(RunLog.id == run_log_id)
                    .values(
                        status="success",
                        finished_at=datetime.utcnow(),
                        news_collected=result.news_collected
                    )
                )
                
            except Exception as e:
                # Update run log with error
                await db.execute(
                    update(RunLog)
                    .where(RunLog.id == run_log_id)
                    .values(
                        status="error",
                        finished_at=datetime.utcnow(),
                        error_message=str(e)
                    )
                )
            
            await db.commit()


# Global scheduler instance
scheduler_service = SchedulerService()
