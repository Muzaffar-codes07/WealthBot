"""Upload ML artifacts to a Hugging Face Hub model repo.

Mirrors the manifest in app/services/artifact_loader.py so the upload
layout cannot drift from what the backend downloads at startup.

Usage:
    huggingface-cli login                                   # one-time, paste write token
    export HF_REPO_ID=MuzCodesStuff/wealthbot-artifacts     # repo must exist (create via UI)
    python scripts/upload_artifacts_hf.py                   # uploads from ml/models/
    python scripts/upload_artifacts_hf.py --dry-run         # list only

Exit codes:
    0  all required files uploaded
    1  env var missing, source file missing, or upload failure
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "_artifact_loader", ROOT / "app" / "services" / "artifact_loader.py"
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
ARTIFACT_FILES = _mod.ARTIFACT_FILES
OPTIONAL_FILES = _mod.OPTIONAL_FILES

SOURCE_DIR = ROOT / "ml" / "models"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List files but do not upload")
    args = parser.parse_args()

    repo_id = os.environ.get("HF_REPO_ID", "").strip()
    if not repo_id:
        print("ERROR: HF_REPO_ID not set", file=sys.stderr)
        return 1

    to_upload: list[tuple[Path, str]] = []
    missing_required: list[str] = []
    for filename in ARTIFACT_FILES:
        src = SOURCE_DIR / filename
        if not src.exists():
            if filename in OPTIONAL_FILES:
                print(f"skip (optional, missing): {filename}")
            else:
                missing_required.append(filename)
            continue
        to_upload.append((src, filename))

    if missing_required:
        print(f"ERROR: missing required source files: {missing_required}", file=sys.stderr)
        return 1

    print(f"Uploading {len(to_upload)} files to {repo_id}:")
    for src, dst in to_upload:
        size_mb = src.stat().st_size / 1024 / 1024
        print(f"  {dst:50s}  ({size_mb:7.2f} MB)")

    if args.dry_run:
        print("\n--dry-run: no upload performed")
        return 0

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("ERROR: huggingface_hub not installed (pip install huggingface_hub)", file=sys.stderr)
        return 1

    api = HfApi()
    for src, dst in to_upload:
        print(f"uploading {dst}...")
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=dst,
            repo_id=repo_id,
            repo_type="model",
        )

    print("\nAll artifacts uploaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
