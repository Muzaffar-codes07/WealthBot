"""
WealthBot Predictions Router
=============================
Safe-to-Spend endpoint with heuristic fall-back when ML model is unavailable.
"""

import calendar
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.db.models import Transaction, TransactionType, User
from app.schemas.prediction import SafeToSpendResponse
from app.services.ml_service import MLService, get_ml_service
from ml.preprocessing.features import extract_user_features

router = APIRouter(tags=["Predictions"])

MIN_TRANSACTIONS_FOR_ML = 10


# =============================================================================
# Safe-to-Spend
# =============================================================================


@router.get(
    "/safe-to-spend",
    response_model=SafeToSpendResponse,
    summary="Get daily Safe-to-Spend amount",
)
async def safe_to_spend(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    ml_service: MLService = Depends(get_ml_service),
) -> SafeToSpendResponse:
    """Calculate the user's safe daily spending limit.

    Uses XGBoost when the model is loaded **and** the user has ≥10
    transactions.  Otherwise falls back to a simple heuristic so the
    frontend always shows a number.

    Results are cached in Redis for 5 minutes when available.
    """
    from app.core.config import settings

    user_id = str(current_user.id)

    # Check Redis cache first
    if settings.redis_enabled:
        from app.core.cache import get_cached_prediction

        cached = await get_cached_prediction(user_id)
        if cached is not None:
            return SafeToSpendResponse(**cached)

    now = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Query current-month expenses
    # ------------------------------------------------------------------
    month_expenses_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionType.EXPENSE.value,
        extract("year", Transaction.transaction_date) == now.year,
        extract("month", Transaction.transaction_date) == now.month,
    )
    month_expenses: Decimal = (await db.execute(month_expenses_q)).scalar_one()

    # Count user's total transactions (for cold-start check)
    txn_count_q = select(func.count()).where(
        Transaction.user_id == current_user.id,
    )
    txn_count: int = (await db.execute(txn_count_q)).scalar_one()

    # ------------------------------------------------------------------
    # Budget parameters
    # ------------------------------------------------------------------
    monthly_income = current_user.monthly_income or Decimal("0")
    savings_goal = current_user.savings_goal or Decimal("0")

    # Auto-detect income from this month's income transactions if
    # the user hasn't manually set monthly_income on their profile.
    if monthly_income == 0:
        detected_income_q = select(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).where(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == TransactionType.INCOME.value,
            extract("year", Transaction.transaction_date) == now.year,
            extract("month", Transaction.transaction_date) == now.month,
        )
        monthly_income = (await db.execute(detected_income_q)).scalar_one()

    last_day = _last_day_of_month(now.year, now.month)
    days_remaining = max(1, (last_day - now.day) + 1)

    # Recurring expenses (current month only to avoid double-counting)
    recurring_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.user_id == current_user.id,
        Transaction.is_recurring.is_(True),
        Transaction.transaction_type == TransactionType.EXPENSE.value,
        extract("year", Transaction.transaction_date) == now.year,
        extract("month", Transaction.transaction_date) == now.month,
    )
    recurring_expenses: Decimal = (await db.execute(recurring_q)).scalar_one()

    # ------------------------------------------------------------------
    # ML path: extract features if model loaded and enough transactions
    # ------------------------------------------------------------------
    use_ml = ml_service._model_loaded and txn_count >= MIN_TRANSACTIONS_FOR_ML
    features = None

    if use_ml:
        # Fetch last 60 days of transactions for feature extraction
        from datetime import timedelta as _timedelta

        cutoff = now - _timedelta(days=60)
        txn_rows = await db.execute(
            select(Transaction)
            .where(
                Transaction.user_id == current_user.id,
                Transaction.transaction_date >= cutoff,
            )
            .order_by(Transaction.transaction_date.desc())
        )
        txn_list = [
            {
                "amount": float(t.amount),
                "transaction_type": t.transaction_type,
                "category": t.category or "Other",
                "is_recurring": t.is_recurring,
                "transaction_date": t.transaction_date,
            }
            for t in txn_rows.scalars().all()
        ]
        features = await run_in_threadpool(
            extract_user_features,
            txn_list,
            float(monthly_income),
            now,
        )

    # ------------------------------------------------------------------
    # Delegate to MLService (handles ML vs heuristic internally)
    # ------------------------------------------------------------------
    result = await ml_service.calculate_safe_to_spend(
        user_id=str(current_user.id),
        monthly_income=monthly_income,
        savings_goal=savings_goal,
        month_expenses=month_expenses,
        recurring_expenses=recurring_expenses,
        days_remaining=days_remaining,
        features=features,
    )

    model_used: Literal["heuristic", "xgboost"] = result["model_used"]
    safe_until = f"{now.year}-{now.month:02d}-{last_day:02d}"

    response = SafeToSpendResponse(
        amount=result["amount"],
        safe_until=safe_until,
        daily_allowance=result["daily_allowance"],
        risk_level=result["risk_level"],
        days_until_payday=days_remaining,
        model_used=model_used,
        is_ml_active=(model_used == "xgboost"),
        recommendations=result["recommendations"],
    )

    # Cache result in Redis
    if settings.redis_enabled:
        from app.core.cache import set_cached_prediction

        await set_cached_prediction(user_id, response.model_dump(mode="json"))

    return response


# =============================================================================
# Helpers
# =============================================================================


def _last_day_of_month(year: int, month: int) -> int:
    """Return the last calendar day for the given year/month."""
    return calendar.monthrange(year, month)[1]
