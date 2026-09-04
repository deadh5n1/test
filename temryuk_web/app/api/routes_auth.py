"""
Authentication routes.
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, create_session_token
from app.config import ADMIN_PASSWORD_HASH

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    """Login page."""
    return request.state.templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_submit(
    request: Request,
    password: str = Form(...),
):
    """Handle login form submission."""
    if not ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin password not configured"
        )

    if not verify_password(password, ADMIN_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )

    response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    token = create_session_token(1)  # user_id = 1 for admin
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    """Handle logout."""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_token")
    return response


async def get_current_user(request: Request) -> bool:
    """Dependency to check if user is authenticated."""
    token = request.cookies.get("session_token")
    if not token:
        return False
    
    user_id = verify_session_token(token)
    return user_id is not None


async def require_auth(request: Request) -> bool:
    """Dependency that requires authentication."""
    if not await get_current_user(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return True
