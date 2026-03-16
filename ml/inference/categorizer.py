"""
WealthBot Transaction Categorizer
===================================
ONNX Runtime inference wrapper for the DistilBERT transaction categorizer.

Loads ``ml/models/categorizer.onnx`` + ``ml/models/tokenizer/`` +
``ml/models/label_encoder.json`` once at startup and exposes a thread-safe
``categorize()`` method.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from transformers import DistilBertTokenizerFast  # type: ignore[attr-defined]

logger = logging.getLogger("wealthbot.ml.categorizer")

# =============================================================================
# TransactionCategorizer
# =============================================================================


class TransactionCategorizer:
    """ONNX Runtime wrapper for the DistilBERT categorizer.

    Instantiated **once** during FastAPI lifespan.  ``categorize()`` is
    thread-safe (ONNX sessions + HuggingFace tokenizers are re-entrant).
    """

    def __init__(
        self,
        model_path: str | Path,
        tokenizer_path: str | Path,
        label_encoder_path: str | Path,
        max_length: int = 64,
    ) -> None:
        model_path = Path(model_path)
        tokenizer_path = Path(tokenizer_path)
        label_encoder_path = Path(label_encoder_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Categorizer ONNX not found: {model_path}")
        if not tokenizer_path.exists():
            raise FileNotFoundError(f"Tokenizer dir not found: {tokenizer_path}")
        if not label_encoder_path.exists():
            raise FileNotFoundError(f"Label encoder not found: {label_encoder_path}")

        # Load ONNX session
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(model_path), sess_options=opts, providers=["CPUExecutionProvider"]
        )

        # Load tokenizer
        self._tokenizer = DistilBertTokenizerFast.from_pretrained(str(tokenizer_path))
        self._max_length = max_length

        # Load label encoder
        with open(label_encoder_path, encoding="utf-8") as f:
            le_data: dict[str, Any] = json.load(f)
        self._id2label: dict[int, str] = {
            int(k): v for k, v in le_data["id2label"].items()
        }
        self._num_labels = len(self._id2label)

        logger.info(
            "TransactionCategorizer loaded (%d labels) from %s",
            self._num_labels,
            model_path,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def categorize(
        self,
        text: str,
        *,
        user_id: str | None = None,
    ) -> tuple[str, float]:
        """Categorize a single transaction text.

        Args:
            text: Merchant name + optional description, e.g.
                  ``"Swiggy online food order"``.
            user_id: Optional user id for structured logging (hashed).

        Returns:
            Tuple of ``(category_label, confidence)`` where confidence
            is in ``[0, 1]``.
        """
        start = time.perf_counter()

        encoding = self._tokenizer(
            text,
            max_length=self._max_length,
            padding="max_length",
            truncation=True,
            return_tensors="np",
        )
        input_ids = encoding["input_ids"].astype(np.int64)
        attention_mask = encoding["attention_mask"].astype(np.int64)

        raw: list[Any] = self._session.run(
            None,
            {"input_ids": input_ids, "attention_mask": attention_mask},
        )
        logits: np.ndarray = raw[0]  # shape (1, num_labels)

        # Softmax
        exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)

        predicted_id = int(np.argmax(probs, axis=1)[0])
        confidence = float(probs[0, predicted_id])
        label = self._id2label[predicted_id]

        latency_ms = (time.perf_counter() - start) * 1000

        self._log_prediction(
            text_preview=text[:50],
            label=label,
            confidence=confidence,
            latency_ms=latency_ms,
            user_id=user_id,
        )

        return label, confidence

    # ------------------------------------------------------------------
    # Structured Logging
    # ------------------------------------------------------------------

    def _log_prediction(
        self,
        *,
        text_preview: str,
        label: str,
        confidence: float,
        latency_ms: float,
        user_id: str | None,
    ) -> None:
        """Emit a structured JSON log line per categorization (no raw PII)."""
        hashed_uid = (
            hashlib.sha256(user_id.encode()).hexdigest()[:12]
            if user_id
            else "anonymous"
        )
        log_payload: dict[str, Any] = {
            "event": "transaction_categorization",
            "model": "distilbert_categorizer",
            "user_hash": hashed_uid,
            "predicted_label": label,
            "confidence": round(confidence, 4),
            "latency_ms": round(latency_ms, 2),
            "text_length": len(text_preview),
        }
        logger.info(json.dumps(log_payload))
