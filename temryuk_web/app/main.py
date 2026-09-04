"""
FastAPI application main entry point.
"""
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import DEBUG
from app.core.database import init_db
from app.services.scheduler_service import scheduler_service
from app.api.routes_digests import router as digests_router
from app.api.routes_sources import router as sources_router
from app.api.routes_news import router as news_router
from app.api.routes_actions import router as actions_router
from app.api.routes_auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    scheduler_service.start()
    
    yield
    
    # Shutdown
    scheduler_service.stop()


app = FastAPI(
    title="Temryuk News",
    description="News collection and digest generation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def add_templates_to_state(request: Request, call_next):
    """Add templates to request state for use in routes."""
    request.state.templates = templates
    response = await call_next(request)
    return response


# Include routers
app.include_router(auth_router)
app.include_router(digests_router)
app.include_router(sources_router)
app.include_router(news_router)
app.include_router(actions_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
