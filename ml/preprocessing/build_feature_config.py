"""Regenerate ml/models/feature_config.json from the canonical feature vector.

The JSON is the **artifact** of the schema encoded in extract_user_features().
Run this any time the feature vector layout changes. The JSON is committed to
the repo so features.py can import at module-load time in every environment
(dev, CI, container) without a separate download step.

    python -m ml.preprocessing.build_feature_config

Model weights (xgboost_spending.onnx, categorizer.onnx, tokenizer/) remain
out-of-repo and are fetched by app.services.artifact_loader at startup.
"""

from __future__ import annotations

import json
from pathlib import Path

FEATURES: list[dict[str, str]] = [
    {"name": "day_of_month", "kind": "temporal"},
    {"name": "day_of_week", "kind": "temporal"},
    {"name": "is_weekend", "kind": "temporal"},
    {"name": "days_until_month_end", "kind": "temporal"},
    {"name": "is_salary_week", "kind": "temporal"},
    {"name": "total_spending_7d", "kind": "spending_window"},
    {"name": "total_spending_30d", "kind": "spending_window"},
    {"name": "avg_daily_spending_7d", "kind": "spending_window"},
    {"name": "avg_daily_spending_30d", "kind": "spending_window"},
    {"name": "spending_trend", "kind": "spending_window"},
    {"name": "max_single_txn_7d", "kind": "spending_window"},
    {"name": "txn_count_7d", "kind": "spending_window"},
    {"name": "txn_count_30d", "kind": "spending_window"},
    {"name": "monthly_income", "kind": "income"},
    {"name": "income_spent_ratio", "kind": "income"},
    {"name": "days_since_last_income", "kind": "income"},
    {"name": "food_pct", "kind": "category_ratio"},
    {"name": "entertainment_pct", "kind": "category_ratio"},
    {"name": "essential_pct", "kind": "category_ratio"},
    {"name": "recurring_expense_total", "kind": "recurring"},
    {"name": "balance_remaining", "kind": "balance"},
]

CATEGORY_GROUPS: dict[str, list[str]] = {
    "food": ["Food", "Coffee", "Groceries"],
    "entertainment": ["Entertainment", "Shopping", "Travel"],
    "essential": ["Housing", "Utilities", "Healthcare", "Insurance", "Transportation"],
}


def main() -> Path:
    out = Path(__file__).resolve().parent.parent / "models" / "feature_config.json"
    config = {
        "version": "v1",
        "feature_count": len(FEATURES),
        "target": "next_7d_spending",
        "features": FEATURES,
        "category_groups": CATEGORY_GROUPS,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(FEATURES)} features)")
    return out


if __name__ == "__main__":
    main()
