"""
WealthBot Predictions Router
=============================
Safe-to-Spend endpoint with heuristic fall-back when ML model is unavailable.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.db.models import Transaction, TransactionType, User
from app.schemas.prediction import SafeToSpendResponse
from app.services.ml_service import MLService, get_ml_service

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
    """
    Calculate the user's safe daily spending limit.

    Uses XGBoost when the model is loaded **and** the user has ≥10
    transactions.  Otherwise falls back to a simple heuristic so the
    frontend always shows a number.
    """
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
    # Determine budget parameters
    # ------------------------------------------------------------------
    monthly_income = current_user.monthly_income or Decimal("0")
    savings_goal = current_user.savings_goal or Decimal("0")

    # Days remaining in the month (including today)
    last_day = _last_day_of_month(now.year, now.month)
    days_remaining = max(1, (last_day - now.day) + 1)

    # ------------------------------------------------------------------
    # ML path vs. heuristic path
    # ------------------------------------------------------------------
    use_ml = ml_service._model_loaded and txn_count >= MIN_TRANSACTIONS_FOR_ML

    if use_ml:
        # Gather recurring expenses for MLService.calculate_safe_to_spend
        recurring_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == current_user.id,
            Transaction.is_recurring.is_(True),
            Transaction.transaction_type == TransactionType.EXPENSE.value,
        )
        recurring_expenses: Decimal = (await db.execute(recurring_q)).scalar_one()

        sts_result = await ml_service.calculate_safe_to_spend(
            user_id=current_user.id,
            current_balance=monthly_income - month_expenses,
            monthly_income=monthly_income,
            monthly_savings_goal=savings_goal,
            recurring_expenses=recurring_expenses,
            days_until_payday=days_remaining,
            recent_transactions=[],
        )
        amount = sts_result.safe_to_spend
        daily_allowance = sts_result.daily_allowance
        risk_level = sts_result.risk_level
        recommendations = sts_result.recommendations
        model_used: Literal["heuristic", "xgboost"] = "xgboost"
        is_ml_active = True
    else:
        # Heuristic: (income − savings − expenses) / days remaining
        remaining_budget = monthly_income - savings_goal - month_expenses
        amount = max(Decimal("0"), remaining_budget)
        daily_allowance = max(
            Decimal("0"),
            (remaining_budget / Decimal(str(days_remaining))).quantize(Decimal("0.01")),
        )
        risk_level = _heuristic_risk(remaining_budget, monthly_income)
        recommendations = _heuristic_recommendations(
            risk_level, days_remaining, remaining_budget
        )
        model_used = "heuristic"
        is_ml_active = False

    safe_until = f"{now.year}-{now.month:02d}-{last_day:02d}"

    return SafeToSpendResponse(
        amount=amount,
        safe_until=safe_until,
        daily_allowance=daily_allowance,
        risk_level=risk_level,
        days_until_payday=days_remaining,
        model_used=model_used,
        is_ml_active=is_ml_active,
        recommendations=recommendations,
    )


# =============================================================================
# Helpers
# =============================================================================


def _last_day_of_month(year: int, month: int) -> int:
    """Return the last calendar day for the given year/month."""
    import calendar

    return calendar.monthrange(year, month)[1]


def _heuristic_risk(remaining: Decimal, income: Decimal) -> str:
    if income <= 0:
        return "high"
    ratio = remaining / income
    if ratio >= Decimal("0.30"):
        return "low"
    if ratio >= Decimal("0.15"):
        return "medium"
    return "high"


def _heuristic_recommendations(
    risk: str, days_left: int, remaining: Decimal
) -> list[str]:
    tips: list[str] = []
    if risk == "high":
        tips.append("Your spending is high — consider cutting discretionary purchases.")
        tips.append("Review recurring subscriptions for potential savings.")
    elif risk == "medium":
        tips.append("You're on track but watch large one-time expenses.")
    else:
        tips.append("Great job! You're well within your budget this month.")

    if days_left <= 5:
        tips.append(f"Only {days_left} day(s) left this month — spend carefully.")
    if remaining <= 0:
        tips.append("You've exceeded your budget. Avoid non-essential spending.")
    return tips
