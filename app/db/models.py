"""
WealthBot SQLAlchemy Models
===========================
Database models for Users and Transactions with financial precision.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# =============================================================================
# Enums
# =============================================================================

class TransactionType(str, Enum):
    """Transaction type enumeration."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    REFUND = "refund"


class TransactionCategory(str, Enum):
    """Transaction category enumeration (PascalCase — single source of truth)."""
    HOUSING = "Housing"
    TRANSPORTATION = "Transportation"
    FOOD = "Food"
    COFFEE = "Coffee"
    GROCERIES = "Groceries"
    TRAVEL = "Travel"
    UTILITIES = "Utilities"
    HEALTHCARE = "Healthcare"
    INSURANCE = "Insurance"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    EDUCATION = "Education"
    SAVINGS = "Savings"
    INVESTMENTS = "Investments"
    DEBT_PAYMENT = "Debt Payment"
    INCOME = "Income"
    OTHER = "Other"


# =============================================================================
# User Model
# =============================================================================

class User(Base):
    """
    User model for WealthBot application.
    
    Stores user authentication and profile information with
    GDPR-compliant PII handling.
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Unique user identifier (UUID)",
    )

    # Authentication Fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address (unique)",
    )
    email_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of email for lookups without exposing PII",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )

    # Profile Fields
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User first name",
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User last name",
    )

    # Account Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether user account is active",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email is verified",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user has admin privileges",
    )

    # Financial Preferences
    monthly_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="User's monthly income for budgeting",
    )
    savings_goal: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="User's monthly savings goal",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        server_default="INR",
        nullable=False,
        comment="User's preferred currency (ISO 4217)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Account creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login timestamp",
    )

    # GDPR Compliance
    data_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when user consented to data processing",
    )
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when user requested account deletion",
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_users_email_hash", "email_hash"),
        Index("ix_users_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation with masked email for security."""
        masked = self.email[:3] + "***" if self.email else "unknown"
        return f"<User(id={self.id}, email={masked})>"


# =============================================================================
# Transaction Model
# =============================================================================

class Transaction(Base):
    """
    Transaction model for financial records.
    
    Uses Numeric(15,2) for precise financial calculations,
    supporting values up to 9,999,999,999,999.99.
    """

    __tablename__ = "transactions"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Unique transaction identifier (UUID)",
    )

    # Foreign Key
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to user who owns this transaction",
    )

    # Transaction Details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Transaction amount with 2 decimal precision",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        server_default="INR",
        nullable=False,
        comment="Transaction currency (ISO 4217)",
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TransactionType.EXPENSE.value,
        comment="Type: income, expense, transfer, refund",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TransactionCategory.OTHER.value,
        index=True,
        comment="Transaction category for budgeting",
    )

    # Description & Metadata
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Transaction description",
    )
    merchant_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Merchant or payee name",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional user notes",
    )

    # ML-Generated Fields
    predicted_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="ML-predicted category (DistilBERT)",
    )
    category_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="Confidence score for predicted category (0-1)",
    )
    is_recurring: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether transaction is recurring",
    )

    # Date Fields
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Date when transaction occurred",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="transactions",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_user_category", "user_id", "category"),
        Index("ix_transactions_date_type", "transaction_date", "transaction_type"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Transaction(id={self.id}, amount={self.amount}, "
            f"type={self.transaction_type}, category={self.category})>"
        )

    @property
    def is_expense(self) -> bool:
        """Check if transaction is an expense."""
        return self.transaction_type == TransactionType.EXPENSE.value

    @property
    def is_income(self) -> bool:
        """Check if transaction is income."""
        return self.transaction_type == TransactionType.INCOME.value
