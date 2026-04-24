"""Download ML model artifacts from S3-compatible object storage at startup.

Called from the FastAPI lifespan **before** MLService.load_models(). If the
required env vars are unset, the loader is a no-op — local dev continues to
use whatever files happen to be on disk, and the MLService heuristic fallback
still works when files are missing.

Required env vars (set only in staging/production):
    ARTIFACT_BUCKET_URL   — e.g. https://<account>.r2.cloudflarestorage.com
    ARTIFACT_BUCKET_NAME  — bucket name, e.g. wealthbot-artifacts
    ARTIFACT_VERSION      — prefix under the bucket, e.g. v1
    ARTIFACT_ACCESS_KEY   — S3 access key ID
    ARTIFACT_SECRET_KEY   — S3 secret access key
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

ARTIFACT_FILES: tuple[tuple[str, str], ...] = (
    ("xgboost_spending.onnx", "xgboost_spending.onnx"),
    ("categorizer.onnx", "categorizer.onnx"),
    ("label_encoder.json", "label_encoder.json"),
    ("tokenizer/tokenizer.json", "tokenizer/tokenizer.json"),
    ("tokenizer/tokenizer_config.json", "tokenizer/tokenizer_config.json"),
    ("tokenizer/vocab.txt", "tokenizer/vocab.txt"),
    ("tokenizer/special_tokens_map.json", "tokenizer/special_tokens_map.json"),
)


def _env() -> dict[str, str] | None:
    required = (
        "ARTIFACT_BUCKET_URL",
        "ARTIFACT_BUCKET_NAME",
        "ARTIFACT_VERSION",
        "ARTIFACT_ACCESS_KEY",
        "ARTIFACT_SECRET_KEY",
    )
    values = {k: os.environ.get(k, "") for k in required}
    if not all(values.values()):
        return None
    return values


def ensure_artifacts(target_dir: Path) -> None:
    """Download artifact files if missing. No-op if env vars unset or files already present."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    env = _env()
    if env is None:
        logger.info(
            "artifact_loader: ARTIFACT_* env vars not set — skipping download "
            "(local dev or heuristic-only deploy)."
        )
        return

    missing = [dst for _, dst in ARTIFACT_FILES if not (target_dir / dst).exists()]
    if not missing:
        logger.info("artifact_loader: all %d artifacts already present on disk", len(ARTIFACT_FILES))
        return

    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "artifact_loader: boto3 not installed but ARTIFACT_* env vars are set. "
            "Install boto3 or unset env vars. Continuing with heuristic fallback."
        )
        return

    s3 = boto3.client(
        "s3",
        endpoint_url=env["ARTIFACT_BUCKET_URL"],
        aws_access_key_id=env["ARTIFACT_ACCESS_KEY"],
        aws_secret_access_key=env["ARTIFACT_SECRET_KEY"],
    )
    bucket = env["ARTIFACT_BUCKET_NAME"]
    prefix = env["ARTIFACT_VERSION"].strip("/")

    for src, dst in ARTIFACT_FILES:
        dst_path = target_dir / dst
        if dst_path.exists():
            continue
        key = f"{prefix}/{src}"
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            s3.download_file(bucket, key, str(dst_path))
        except Exception as exc:
            logger.warning(
                "artifact_loader: failed to download s3://%s/%s: %s "
                "(MLService will fall back to heuristic for this artifact)",
                bucket,
                key,
                exc,
            )
            continue

        size = dst_path.stat().st_size
        sha = hashlib.sha256(dst_path.read_bytes()).hexdigest()[:12]
        logger.info(
            "artifact_loader: downloaded %s (%d bytes, sha256=%s…)",
            dst,
            size,
            sha,
        )
