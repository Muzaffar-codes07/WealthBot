"""
WealthBot Users & Auth Router
==============================
User registration, login, profile CRUD, and account management.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_pii,
    verify_password,
)
from app.db.database import get_db_session
from app.db.models import User
from app.schemas.common import MessageResponse
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(prefix="/users", tags=["Users"])


# =============================================================================
# Authentication Endpoints
# =============================================================================


@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Create a new user account with hashed password."""
    _ = request
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        email_hash=hash_pii(body.email.lower()),
        hashed_password=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        monthly_income=body.monthly_income,
        savings_goal=body.savings_goal,
        currency=body.currency,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@auth_router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtain JWT access and refresh tokens",
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate with email/password and receive access + refresh JWTs."""
    _ = request
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    user.last_login_at = datetime.now(UTC)
    await db.flush()

    from app.core.config import settings

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a refresh token",
)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Validate refresh token and issue a new access + refresh token pair."""
    _ = request

    token_data = decode_refresh_token(body.refresh_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    from app.core.config import settings

    new_access = create_access_token(subject=user.id)
    new_refresh = create_refresh_token(subject=user.id)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# =============================================================================
# User Profile Endpoints
# =============================================================================


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user's profile."""
    return current_user


@users_router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_profile(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Update the authenticated user's profile fields."""
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)
    return current_user


@users_router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Deactivate current user account",
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Soft-delete: deactivate the account and record deletion request."""
    current_user.is_active = False
    current_user.deletion_requested_at = datetime.now(UTC)
    await db.flush()
    return MessageResponse(message="Account deactivated successfully")
