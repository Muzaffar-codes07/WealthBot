"""
Seed Student Account
====================
Creates a realistic student persona with 7,400+ synthetic transactions
for local development and testing.

Usage (pick one):

  # Option A — Backend is running on port 8000:
  python scripts/seed_dummy_account.py

  # Option B — Only database is running (no backend):
  python scripts/seed_dummy_account.py --direct

Credentials:
  Set DEMO_EMAIL and DEMO_PASSWORD env vars (see DEMO_ACCESS.md).
  The script refuses to run without them.
"""

import argparse
import asyncio
import csv
import hashlib
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Account details ──────────────────────────────────────────────────────────
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "").strip()
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "").strip()
if not DEMO_EMAIL or not DEMO_PASSWORD:
    raise SystemExit(
        "DEMO_EMAIL and DEMO_PASSWORD env vars are required. "
        "See DEMO_ACCESS.md (gitignored) for local values."
    )
DEMO_FIRST_NAME = "Swarna"
DEMO_LAST_NAME = "Student"
DEMO_MONTHLY_INCOME = Decimal("50000.00")
DEMO_SAVINGS_GOAL = Decimal("10000.00")
DEMO_CURRENCY = "INR"

SYNTHETIC_CSV = ROOT / "ml" / "models" / "synthetic_transactions.csv"


# =============================================================================
# Option A — Via HTTP (requires running backend)
# =============================================================================

def seed_via_api() -> None:
    """Register the account and bulk-insert transactions through the REST API."""
    import httpx  # noqa: delay import

    base = "http://localhost:8000"

    payload = {
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "first_name": DEMO_FIRST_NAME,
        "last_name": DEMO_LAST_NAME,
        "monthly_income": float(DEMO_MONTHLY_INCOME),
        "savings_goal": float(DEMO_SAVINGS_GOAL),
        "currency": DEMO_CURRENCY,
    }

    # 1. Register
    print(f"Registering {DEMO_EMAIL} via API …")
    try:
        resp = httpx.post(f"{base}/api/v1/auth/register", json=payload, timeout=10)
    except httpx.ConnectError:
        print(
            "ERROR: Could not connect to backend at http://localhost:8000.\n"
            "Start the backend first:\n"
            "  uvicorn app.main:app --reload --port 8000\n"
            "Or use --direct flag to seed via database directly."
        )
        sys.exit(1)

    if resp.status_code == 201:
        print("User created successfully.")
    elif resp.status_code == 409:
        print("User already exists — skipping registration.")
    else:
        print(f"Registration failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    # 2. Login to get token
    print("Logging in …")
    resp = httpx.post(
        f"{base}/api/v1/auth/token",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"Login failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    token = resp.json()["access_token"]
    print(f"Login successful! Token (first 20 chars): {token[:20]}…")

    # 3. Seed transactions via API (one at a time — slow but works without DB access)
    headers = {"Authorization": f"Bearer {token}"}
    rows = _load_csv_rows()
    print(f"Seeding {len(rows)} transactions via API (this may take a while) …")

    success = 0
    for i, row in enumerate(rows):
        txn_payload = {
            "amount": float(row["amount"]),
            "currency": row["currency"],
            "transaction_type": row["transaction_type"],
            "category": row["category"],
            "description": row["description"],
            "merchant_name": row["merchant_name"],
            "is_recurring": row["is_recurring"] == "True",
            "transaction_date": row["transaction_date"],
        }
        resp = httpx.post(
            f"{base}/api/v1/transactions/",
            json=txn_payload,
            headers=headers,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            success += 1
        if (i + 1) % 500 == 0:
            print(f"  … {i + 1}/{len(rows)} inserted")

    print(f"Transactions seeded: {success}/{len(rows)}")
    _print_credentials()


# =============================================================================
# Option B — Direct DB insert (requires only PostgreSQL)
# =============================================================================

async def seed_via_db() -> None:
    """Insert user + transactions directly into the database."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import settings
    from app.core.security import hash_password
    from app.db.models import Base, Transaction, User

    db_url = settings.database_url
    is_sqlite = db_url.startswith("sqlite")
    display = db_url.split("///")[-1] if is_sqlite else db_url.split("@")[-1]
    print(f"Connecting to database: {display} …")

    kwargs: dict = {"echo": False}
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(db_url, **kwargs)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables ensured.")

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # ── 1. Create or find user ───────────────────────────────────────
        result = await session.execute(
            select(User).where(User.email == DEMO_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            user_id = existing.id
            print(f"User {DEMO_EMAIL} already exists (id={user_id}) — skipping user creation.")
        else:
            user = User(
                email=DEMO_EMAIL,
                email_hash=hashlib.sha256(DEMO_EMAIL.encode()).hexdigest(),
                hashed_password=hash_password(DEMO_PASSWORD),
                first_name=DEMO_FIRST_NAME,
                last_name=DEMO_LAST_NAME,
                monthly_income=DEMO_MONTHLY_INCOME,
                savings_goal=DEMO_SAVINGS_GOAL,
                currency=DEMO_CURRENCY,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()
            user_id = user.id
            print(f"User created (id={user_id}).")

        # ── 2. Check if transactions already exist ───────────────────────
        txn_count_result = await session.execute(
            select(Transaction).where(Transaction.user_id == user_id).limit(1)
        )
        if txn_count_result.scalar_one_or_none():
            print("Transactions already seeded for this user — skipping.")
            await session.commit()
            await engine.dispose()
            _print_credentials()
            return

        # ── 3. Bulk insert transactions ──────────────────────────────────
        rows = _load_csv_rows()
        print(f"Inserting {len(rows)} transactions …")

        batch: list[Transaction] = []
        for row in rows:
            txn = Transaction(
                id=str(uuid4()),
                user_id=user_id,
                amount=Decimal(row["amount"]),
                currency=row["currency"],
                transaction_type=row["transaction_type"],
                category=row["category"],
                description=row["description"],
                merchant_name=row["merchant_name"],
                is_recurring=row["is_recurring"] == "True",
                transaction_date=datetime.fromisoformat(row["transaction_date"]),
            )
            batch.append(txn)

            # Flush in batches of 1000 for memory efficiency
            if len(batch) >= 1000:
                session.add_all(batch)
                await session.flush()
                inserted = len(rows) - len(batch) + 1000  # approximate
                print(f"  ... {min(inserted, len(rows))} / {len(rows)} flushed")
                batch.clear()

        # Flush remaining
        if batch:
            session.add_all(batch)
            await session.flush()

        await session.commit()
        print(f"All {len(rows)} transactions inserted and bound to user {user_id}.")

    await engine.dispose()
    _print_credentials()


# =============================================================================
# Helpers
# =============================================================================

def _load_csv_rows() -> list[dict]:
    """Load synthetic transactions from CSV."""
    if not SYNTHETIC_CSV.exists():
        print(f"ERROR: Synthetic data not found at {SYNTHETIC_CSV}")
        print("Run the generator first:")
        print("  python ml/preprocessing/synthetic_data.py")
        sys.exit(1)

    with open(SYNTHETIC_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} transactions from {SYNTHETIC_CSV.name}")
    return rows


def _print_credentials() -> None:
    print("\n" + "=" * 50)
    print("  WEALTHBOT STUDENT ACCOUNT")
    print("=" * 50)
    print(f"  Email:    {DEMO_EMAIL}")
    print(f"  Password: {DEMO_PASSWORD}")
    print(f"  Name:     {DEMO_FIRST_NAME} {DEMO_LAST_NAME}")
    print(f"  Income:   INR {DEMO_MONTHLY_INCOME:,.2f}/mo")
    print(f"  Currency: {DEMO_CURRENCY}")
    print("=" * 50)
    print("\nUse these on http://localhost:3000/login\n")


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed a WealthBot student account with transactions.")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Insert directly into PostgreSQL (skip HTTP API).",
    )
    args = parser.parse_args()

    if args.direct:
        asyncio.run(seed_via_db())
    else:
        seed_via_api()
