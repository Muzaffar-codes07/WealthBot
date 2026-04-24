"""Upload ML artifacts to the Cloudflare R2 bucket consumed by artifact_loader.

Mirrors the ARTIFACT_FILES manifest in app/services/artifact_loader.py so the
upload layout cannot drift from what the backend downloads at startup.

Usage (after running training):
    export ARTIFACT_BUCKET_URL=https://<account>.r2.cloudflarestorage.com
    export ARTIFACT_BUCKET_NAME=wealthbot-artifacts
    export ARTIFACT_VERSION=v1
    export ARTIFACT_ACCESS_KEY=<r2-access-key-id>
    export ARTIFACT_SECRET_KEY=<r2-secret-access-key>
    python scripts/upload_artifacts.py            # uploads from ml/models/
    python scripts/upload_artifacts.py --dry-run  # list only

Exit codes:
    0  all files uploaded (or already present with --skip-existing)
    1  env var missing, source file missing, or upload failure
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "_artifact_loader", ROOT / "app" / "services" / "artifact_loader.py"
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
ARTIFACT_FILES = _mod.ARTIFACT_FILES

REQUIRED_ENV = (
    "ARTIFACT_BUCKET_URL",
    "ARTIFACT_BUCKET_NAME",
    "ARTIFACT_VERSION",
    "ARTIFACT_ACCESS_KEY",
    "ARTIFACT_SECRET_KEY",
)


def _check_env() -> dict[str, str]:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        sys.exit(f"FATAL: missing env vars: {', '.join(missing)}")
    return {k: os.environ[k] for k in REQUIRED_ENV}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("ml/models"),
        help="Local directory containing trained artifacts (default: ml/models)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip upload if the object already exists in the bucket",
    )
    args = parser.parse_args()

    src_dir: Path = args.source
    if not src_dir.is_dir():
        sys.exit(f"FATAL: source dir not found: {src_dir}")

    missing = [s for s, _ in ARTIFACT_FILES if not (src_dir / s).is_file()]
    if missing:
        sys.exit(
            "FATAL: missing local artifacts (run training first):\n  "
            + "\n  ".join(missing)
        )

    env = _check_env()
    prefix = env["ARTIFACT_VERSION"].strip("/")
    bucket = env["ARTIFACT_BUCKET_NAME"]

    if args.dry_run:
        print(f"DRY RUN — would upload to s3://{bucket}/{prefix}/")
        for src, _ in ARTIFACT_FILES:
            local = src_dir / src
            sha = hashlib.sha256(local.read_bytes()).hexdigest()[:12]
            print(f"  {src}  ({local.stat().st_size:>9} B  sha256={sha}…)")
        return 0

    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client(
        "s3",
        endpoint_url=env["ARTIFACT_BUCKET_URL"],
        aws_access_key_id=env["ARTIFACT_ACCESS_KEY"],
        aws_secret_access_key=env["ARTIFACT_SECRET_KEY"],
    )

    for src, dst in ARTIFACT_FILES:
        local = src_dir / src
        key = f"{prefix}/{dst}"

        if args.skip_existing:
            try:
                s3.head_object(Bucket=bucket, Key=key)
                print(f"  skip  {key} (already in bucket)")
                continue
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in {"404", "NoSuchKey"}:
                    raise

        sha = hashlib.sha256(local.read_bytes()).hexdigest()[:12]
        s3.upload_file(str(local), bucket, key)
        print(f"  put   {key}  ({local.stat().st_size:>9} B  sha256={sha}…)")

    print(f"\nDone. Set these on Railway to pull on next boot:")
    for k in REQUIRED_ENV:
        print(f"  {k}={env[k] if k != 'ARTIFACT_SECRET_KEY' else '***'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
