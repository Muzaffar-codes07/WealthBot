"""
WealthBot Pydantic Schemas Package
===================================
Request/Response schemas for API validation.
"""

from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.insights import (
    AIChatRequest,
    AIChatResponse,
    CategorySpendingComparison,
    SpendingVelocityResponse,
    StatementUploadResponse,
    SubscriptionInsight,
    SubscriptionsResponse,
    WeeklyVelocityPoint,
)
from app.schemas.prediction import SafeToSpendResponse, SpendingPredictionResponse
from app.schemas.transaction import (
    CategoryUpdateRequest,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    "CategoryUpdateRequest",
    "CategorySpendingComparison",
    "AIChatRequest",
    "AIChatResponse",
    "LoginRequest",
    "MessageResponse",
    "PaginatedResponse",
    "SafeToSpendResponse",
    "SpendingVelocityResponse",
    "SpendingPredictionResponse",
    "StatementUploadResponse",
    "SubscriptionInsight",
    "SubscriptionsResponse",
    "TokenResponse",
    "TransactionCreate",
    "TransactionResponse",
    "TransactionUpdate",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "WeeklyVelocityPoint",
]
