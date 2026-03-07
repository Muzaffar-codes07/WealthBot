"""
WealthBot Transactions Router
==============================
Transaction CRUD with pagination, search, and ownership enforcement.
"""

import math
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.db.models import Transaction, User
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    CategoryUpdateRequest,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# =============================================================================
# Helpers
# =============================================================================


async def _get_user_transaction(
    transaction_id: str,
    user_id: str,
    db: AsyncSession,
) -> Transaction:
    """Fetch a transaction ensuring it belongs to the requesting user."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    txn = result.scalar_one_or_none()
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return txn


# =============================================================================
# List / Search
# =============================================================================


@router.get(
    "",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List transactions (paginated)",
)
async def list_transactions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[TransactionResponse]:
    """Return paginated transactions for the current user with optional search."""
    base = select(Transaction).where(Transaction.user_id == current_user.id)

    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                Transaction.merchant_name.ilike(pattern),
                Transaction.description.ilike(pattern),
                Transaction.category.ilike(pattern),
            )
        )

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    # Fetch page
    rows = await db.execute(
        base.order_by(Transaction.transaction_date.desc()).limit(limit).offset(offset)
    )
    transactions = list(rows.scalars().all())

    page = (offset // limit) + 1
    total_pages = max(1, math.ceil(total / limit))

    return PaginatedResponse[TransactionResponse](
        data=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
    )


# =============================================================================
# CRUD
# =============================================================================


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transaction",
)
async def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Transaction:
    """Create a new transaction for the current user."""
    txn = Transaction(
        user_id=current_user.id,
        amount=body.amount,
        currency=body.currency,
        transaction_type=body.transaction_type.value,
        category=body.category.value,
        description=body.description,
        merchant_name=body.merchant_name,
        notes=body.notes,
        is_recurring=body.is_recurring,
        transaction_date=body.transaction_date or datetime.now(UTC),
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)
    return txn


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get a single transaction",
)
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Transaction:
    """Retrieve a transaction by ID (ownership enforced)."""
    return await _get_user_transaction(transaction_id, current_user.id, db)


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update a transaction",
)
async def update_transaction(
    transaction_id: str,
    body: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Transaction:
    """Update transaction fields (ownership enforced)."""
    txn = await _get_user_transaction(transaction_id, current_user.id, db)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if (
            field == "transaction_type"
            and value is not None
            or field == "category"
            and value is not None
        ):
            value = value.value
        setattr(txn, field, value)

    await db.flush()
    await db.refresh(txn)
    return txn


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction",
)
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a transaction by ID (ownership enforced)."""
    txn = await _get_user_transaction(transaction_id, current_user.id, db)
    await db.delete(txn)
    await db.flush()


# =============================================================================
# Category Patch
# =============================================================================


@router.patch(
    "/{transaction_id}/category",
    response_model=TransactionResponse,
    summary="Update transaction category",
)
async def update_category(
    transaction_id: str,
    body: CategoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Transaction:
    """Patch only the category of a transaction (matches frontend hook)."""
    txn = await _get_user_transaction(transaction_id, current_user.id, db)
    txn.category = body.category.value
    await db.flush()
    await db.refresh(txn)
    return txn
