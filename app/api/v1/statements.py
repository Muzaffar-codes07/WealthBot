"""
WealthBot Statement Upload Router
=================================
Statement ingestion endpoints for transaction import.
"""

import csv
import io
import re
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.database import get_db_session
from app.db.models import Transaction, TransactionCategory, TransactionType, User
from app.schemas.insights import StatementUploadResponse
from app.services.ml_service import MLService, get_ml_service

router = APIRouter(prefix="/statements", tags=["Statements"])

PDF_ROW_PATTERN = re.compile(
    r"^(?P<date>\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})\s+"
    r"(?P<description>.+?)\s+"
    r"(?P<amount>-?\d[\d,]*(?:\.\d{1,2})?)"
    r"(?:\s+(?P<type>CR|DR|CREDIT|DEBIT))?$",
    flags=re.IGNORECASE,
)

# Keywords that indicate an income/credit transaction
_INCOME_KEYWORDS = re.compile(
    r"(?:SALARY|REFUND|CASHBACK|REVERSAL|INTEREST\s*CREDIT|DIVIDEND|"
    r"REWARD|CREDIT\s*FROM|NEFT\s*CR|RTGS\s*CR|IMPS\s*CR)",
    flags=re.IGNORECASE,
)

# Prefix pattern for Indian bank narrations: UPI-, IMPS-, NEFT-, POS-, etc.
_BANK_PREFIX = re.compile(
    r"^(?:UPI|IMPS|NEFT|RTGS|POS|ATM|ECS|NACH|MMT|BIL|CMS|ACH)[-/]",
    flags=re.IGNORECASE,
)

# Phone numbers, VPA handles, reference numbers to strip from display
_NOISE_PATTERNS = re.compile(
    r"(?:\d{10,}|[a-zA-Z0-9._%+-]+@[a-z]+|Ref\s*(?:No)?\.?\s*\d+)",
    flags=re.IGNORECASE,
)


def _resolve_field(
    row: dict[str, str],
    candidates: list[str],
) -> str | None:
    lowered = {k.lower().strip(): v for k, v in row.items()}
    for key in candidates:
        value = lowered.get(key)
        if value is not None and value.strip() != "":
            return value.strip()
    return None


def _parse_date(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)

    patterns = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    return datetime.now(UTC)


def _parse_csv_rows(content: bytes) -> list[dict[str, str]]:
    decoded = content.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(decoded))
    rows: list[dict[str, str]] = []
    for row in reader:
        normalized = {str(key): str(value) for key, value in row.items()}
        rows.append(normalized)
    return rows


def _parse_pdf_rows(content: bytes) -> list[dict[str, str]]:
    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF parsing dependency is not installed.",
        ) from exc

    rows: list[dict[str, str]] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                match = PDF_ROW_PATTERN.match(line)
                if match is None:
                    continue

                row = {
                    "date": match.group("date") or "",
                    "description": match.group("description") or "",
                    "amount": match.group("amount") or "",
                    "type": (match.group("type") or "debit").lower(),
                    "currency": "INR",
                }
                rows.append(row)

    return rows


def _extract_merchant_name(raw_description: str) -> str:
    """Extract a clean, human-readable merchant name from a raw bank narration.

    Examples:
        UPI-SWIGGY*INSTAMART-ORDER       → Swiggy Instamart
        POS-APOLLO-PHARMACY-HYD           → Apollo Pharmacy
        IMPS-FRIEND-SPLITWISE-REFUND      → Splitwise
        UPI-RAPIDO-BIKE-RIDE-998...@paytm → Rapido Bike Ride
        NEFT-SALARY-APR-2025              → Salary Apr 2025
        AWS-CLOUD-SERVICES-BILLING        → Aws Cloud Services
    """
    text = raw_description.strip()

    # 1. Strip common bank prefixes (UPI-, IMPS-, POS-, etc.)
    text = _BANK_PREFIX.sub("", text)

    # 2. Strip trailing noise (phone numbers, VPA handles, ref numbers)
    text = _NOISE_PATTERNS.sub("", text)

    # 3. Replace hyphens and asterisks with spaces
    text = text.replace("-", " ").replace("*", " ").replace("_", " ")

    # 4. Collapse whitespace and strip
    text = re.sub(r"\s+", " ", text).strip()

    # 5. Remove trailing single-word city codes (HYD, MUM, BLR, DEL, etc.)
    # Only strip if the remaining text has more than 2 words
    words = text.split()
    if len(words) > 2:
        last = words[-1].upper()
        # Common 3-letter Indian city/airport codes and suffixes
        city_codes = {
            "HYD", "MUM", "BLR", "DEL", "CHN", "KOL", "PUN", "BOM",
            "AMD", "GOA", "JAI", "LKO", "AMB", "IND", "NAG", "PAT",
            "MUMBAI", "DELHI", "HYDERABAD", "BANGALORE", "CHENNAI",
            "KOLKATA", "PUNE", "ORDER", "BILLING", "PAYMENT",
        }
        if last in city_codes:
            words = words[:-1]
        text = " ".join(words)

    # 6. Title-case
    text = text.title()

    return text if text else raw_description.strip()


def _clean_description(raw: str) -> str:
    """Clean a raw bank narration into a readable description."""
    text = raw.strip()
    text = text.replace("-", " ").replace("*", " ").replace("_", " ")
    text = _NOISE_PATTERNS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.title() if text else raw.strip()


def _detect_income(description: str, tx_type: str) -> str:
    """Check if the narration indicates an income transaction."""
    if tx_type == TransactionType.INCOME.value:
        return tx_type
    if _INCOME_KEYWORDS.search(description):
        return TransactionType.INCOME.value
    return tx_type


@router.post(
    "/upload",
    response_model=StatementUploadResponse,
    summary="Upload and parse bank statement",
)
@limiter.limit("5/minute")
async def upload_statement(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    ml_service: MLService = Depends(get_ml_service),
) -> StatementUploadResponse:
    """Parse a CSV/PDF statement and create transactions in bulk.

    Automatically extracts clean merchant names from raw bank narrations
    and runs ML categorization when no category is provided.
    """
    _ = request

    filename = (file.filename or "").lower()
    detected_file_type = ""

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if filename.endswith(".csv"):
        rows = _parse_csv_rows(content)
        detected_file_type = "csv"
    elif filename.endswith(".pdf"):
        rows = _parse_pdf_rows(content)
        detected_file_type = "pdf"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and PDF statement uploads are supported.",
        )

    created_count = 0
    skipped_count = 0
    valid_categories = {member.value for member in TransactionCategory}

    for row in rows:
        raw_amount = _resolve_field(row, ["amount", "debit", "credit", "txn amount"])
        if raw_amount is None:
            skipped_count += 1
            continue

        sanitized = raw_amount.replace(",", "").replace("₹", "").strip()
        try:
            amount = Decimal(sanitized)
        except Exception:
            skipped_count += 1
            continue

        tx_type_raw = _resolve_field(row, ["transaction_type", "type", "dr_cr"])
        tx_type = TransactionType.EXPENSE.value
        if tx_type_raw:
            lowered = tx_type_raw.lower()
            if lowered in {"credit", "cr", "income"}:
                tx_type = TransactionType.INCOME.value
            elif lowered in {"debit", "dr", "expense"}:
                tx_type = TransactionType.EXPENSE.value
        elif amount < 0:
            tx_type = TransactionType.EXPENSE.value
            amount = abs(amount)

        if amount == 0:
            skipped_count += 1
            continue

        merchant_name = _resolve_field(row, ["merchant", "merchant_name", "payee"])
        description = _resolve_field(row, ["description", "narration", "remarks"])
        category = _resolve_field(row, ["category"])
        currency = _resolve_field(row, ["currency"]) or "INR"

        # --- Smart extraction from raw bank narrations ---
        if description:
            # Auto-detect income from narration keywords
            tx_type = _detect_income(description, tx_type)

            # Extract clean merchant name if not provided
            if not merchant_name:
                merchant_name = _extract_merchant_name(description)

            # Clean up the description for display
            description = _clean_description(description)

        # --- ML auto-categorization ---
        predicted_category: str | None = None
        category_confidence: float | None = None

        if category not in valid_categories:
            category = TransactionCategory.OTHER.value

        # Run ML categorizer when category is Other and we have text
        if category == TransactionCategory.OTHER.value and (merchant_name or description):
            text = " ".join(filter(None, [merchant_name, description]))
            try:
                pred_cat, pred_conf = await ml_service.categorize_transaction(
                    text, user_id=str(current_user.id)
                )
                if pred_cat is not None:
                    predicted_category = pred_cat
                    category_confidence = pred_conf
                    category = pred_cat
            except Exception:
                pass  # Fall back to Other if ML fails

        transaction_date = _parse_date(_resolve_field(row, ["date", "transaction_date"]))

        db.add(
            Transaction(
                user_id=current_user.id,
                amount=amount,
                currency=currency,
                transaction_type=tx_type,
                category=category,
                description=description,
                merchant_name=merchant_name,
                predicted_category=predicted_category,
                category_confidence=predicted_category and category_confidence,
                transaction_date=transaction_date,
            )
        )
        created_count += 1

    if created_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid rows were found in the uploaded statement.",
        )

    await db.flush()
    return StatementUploadResponse(
        created_count=created_count,
        skipped_count=skipped_count,
        detected_file_type=detected_file_type,
        message=f"Imported {created_count} transactions successfully.",
    )
