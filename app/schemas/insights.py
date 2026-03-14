"""
WealthBot Insights Schemas
==========================
Schemas for analytics, statement upload, and AI assistant endpoints.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class WeeklyVelocityPoint(BaseModel):
    """Weekly cumulative spending comparison point."""

    week: str
    this_month: Decimal
    last_month: Decimal


class CategorySpendingComparison(BaseModel):
    """Category-level spending comparison for this month vs last month."""

    category: str
    this_month: Decimal
    last_month: Decimal


class SpendingVelocityResponse(BaseModel):
    """Aggregated spending velocity payload for analytics page."""

    weekly: list[WeeklyVelocityPoint]
    categories: list[CategorySpendingComparison]


class SubscriptionInsight(BaseModel):
    """Detected recurring payment record."""

    merchant_name: str
    amount: Decimal
    currency: str
    frequency: str
    occurrences: int
    last_charge_date: date
    next_due_date: date
    next_due_in_days: int


class SubscriptionsResponse(BaseModel):
    """Recurring subscription analysis response."""

    subscriptions: list[SubscriptionInsight]
    total_monthly_commitment: Decimal


class StatementUploadResponse(BaseModel):
    """Statement ingestion summary."""

    created_count: int
    skipped_count: int
    detected_file_type: str
    message: str


class AIChatRequest(BaseModel):
    """AI assistant request payload."""

    message: str = Field(min_length=1, max_length=1000)


class AIChatResponse(BaseModel):
    """AI assistant response payload."""

    reply: str
    suggestions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
