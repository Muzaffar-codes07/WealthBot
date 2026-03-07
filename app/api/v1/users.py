"""
WealthBot Users & Auth Router
==============================
User registration, login, profile CRUD, and account management.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db_session
from app.db.models import User
from app.schemas.common import MessageResponse
from app.schemas.user import (
    LoginRequest,
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
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Create a new user account with hashed password."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
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
    summary="Obtain JWT access token",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate with email/password and receive a JWT."""
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

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


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
