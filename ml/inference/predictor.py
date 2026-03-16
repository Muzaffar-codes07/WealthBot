"""
WealthBot Spending Predictor
=============================
ONNX Runtime inference wrapper for the XGBoost spending model.

Loads ``ml/models/xgboost_spending.onnx`` once at startup and exposes a
thread-safe ``predict()`` method that returns a point estimate plus a
95 % confidence interval.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

logger = logging.getLogger("wealthbot.ml.predictor")

# =============================================================================
# Constants
# =============================================================================

# Empirical residual std-dev from training evaluation (RMSE ≈ ₹994)
_RESIDUAL_STD: float = 994.0
_Z_95: float = 1.96  # z-score for 95 % CI


# =============================================================================
# SpendingPredictor
# =============================================================================


class SpendingPredictor:
    """ONNX Runtime wrapper for the XGBoost spending model.

    Designed to be instantiated **once** during FastAPI lifespan and shared
    across all request threads.  ``predict()`` is thread-safe because ONNX
    Runtime sessions handle concurrent ``run()`` calls internally.
    """

    def __init__(self, model_path: str | Path) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"XGBoost ONNX model not found: {model_path}")

        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(model_path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._input_name: str = self._session.get_inputs()[0].name
        logger.info("SpendingPredictor loaded from %s", model_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        features: np.ndarray,
        *,
        user_id: str | None = None,
    ) -> tuple[float, float, float]:
        """Run inference and return ``(prediction, lower_ci, upper_ci)``.

        Args:
            features: float32 array of shape ``(21,)`` or ``(1, 21)``.
            user_id: Optional user id for structured logging (hashed).

        Returns:
            Tuple of ``(predicted_spending, lower_95, upper_95)`` in INR.
        """
        start = time.perf_counter()

        x = features.astype(np.float32)
        if x.ndim == 1:
            x = x.reshape(1, -1)

        raw: list[Any] = self._session.run(None, {self._input_name: x})
        prediction = float(raw[0].flat[0])

        lower = max(0.0, prediction - _Z_95 * _RESIDUAL_STD)
        upper = prediction + _Z_95 * _RESIDUAL_STD

        latency_ms = (time.perf_counter() - start) * 1000

        self._log_prediction(
            features=x[0],
            prediction=prediction,
            lower=lower,
            upper=upper,
            latency_ms=latency_ms,
            user_id=user_id,
        )

        return prediction, lower, upper

    # ------------------------------------------------------------------
    # Structured Logging
    # ------------------------------------------------------------------

    def _log_prediction(
        self,
        *,
        features: np.ndarray,
        prediction: float,
        lower: float,
        upper: float,
        latency_ms: float,
        user_id: str | None,
    ) -> None:
        """Emit a structured JSON log line per prediction (no PII)."""
        hashed_uid = (
            hashlib.sha256(user_id.encode()).hexdigest()[:12]
            if user_id
            else "anonymous"
        )
        log_payload: dict[str, Any] = {
            "event": "spending_prediction",
            "model": "xgboost_spending",
            "user_hash": hashed_uid,
            "prediction": round(prediction, 2),
            "lower_ci": round(lower, 2),
            "upper_ci": round(upper, 2),
            "latency_ms": round(latency_ms, 2),
            "feature_summary": {
                "day_of_month": float(features[0]),
                "monthly_income": float(features[13]),
                "total_spending_30d": float(features[6]),
                "spending_trend": float(features[9]),
            },
        }
        logger.info(json.dumps(log_payload))
