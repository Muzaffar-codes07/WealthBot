"""Download ML model artifacts from Hugging Face Hub at startup.

Called from the FastAPI lifespan **before** MLService.load_models(). If the
required env vars are unset, the loader is a no-op — local dev continues to
use whatever files happen to be on disk, and the MLService heuristic fallback
still works when files are missing.

Required env vars (set only in staging/production):
    HF_REPO_ID    — e.g. MuzCodesStuff/wealthbot-artifacts
    HF_TOKEN      — required for private repos (omit for public)

Optional:
    HF_REVISION   — git revision (branch/tag/commit), defaults to "main"
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

ARTIFACT_FILES: tuple[str, ...] = (
    "xgboost_spending.onnx",
    "categorizer.onnx",
    "categorizer.onnx.data",
    "label_encoder.json",
    "tokenizer/tokenizer.json",
    "tokenizer/tokenizer_config.json",
    "tokenizer/vocab.txt",
    "tokenizer/special_tokens_map.json",
)

# Files the ONNX runtime / tokenizer can load without; missing them is a warning, not an error.
OPTIONAL_FILES: frozenset[str] = frozenset({
    "tokenizer/vocab.txt",
    "tokenizer/special_tokens_map.json",
})


def _env() -> tuple[str, str | None, str] | None:
    repo_id = os.environ.get("HF_REPO_ID", "").strip()
    if not repo_id:
        return None
    token = os.environ.get("HF_TOKEN") or None
    revision = os.environ.get("HF_REVISION", "main")
    return repo_id, token, revision


def ensure_artifacts(target_dir: Path) -> None:
    """Download artifact files if missing. No-op if HF_REPO_ID unset or files already present."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    env = _env()
    if env is None:
        logger.info(
            "artifact_loader: HF_REPO_ID not set — skipping download "
            "(local dev or heuristic-only deploy)."
        )
        return
    repo_id, token, revision = env

    missing = [f for f in ARTIFACT_FILES if not (target_dir / f).exists()]
    if not missing:
        logger.info(
            "artifact_loader: all %d artifacts already present on disk",
            len(ARTIFACT_FILES),
        )
        return

    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError
    except ImportError:
        logger.warning(
            "artifact_loader: huggingface_hub not installed but HF_REPO_ID is set. "
            "Install huggingface_hub or unset env var. Continuing with heuristic fallback."
        )
        return

    for filename in missing:
        try:
            local_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                revision=revision,
                token=token,
                local_dir=str(target_dir),
            )
        except EntryNotFoundError:
            log = logger.info if filename in OPTIONAL_FILES else logger.warning
            log(
                "artifact_loader: %s not in HF repo %s@%s%s",
                filename,
                repo_id,
                revision,
                " (optional)" if filename in OPTIONAL_FILES else "",
            )
            continue
        except Exception as exc:
            logger.warning(
                "artifact_loader: failed to download %s from HF repo %s@%s: %s "
                "(MLService will fall back to heuristic for this artifact)",
                filename,
                repo_id,
                revision,
                exc,
            )
            continue

        path = Path(local_path)
        size = path.stat().st_size
        sha = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        logger.info(
            "artifact_loader: downloaded %s (%d bytes, sha256=%s…)",
            filename,
            size,
            sha,
        )
