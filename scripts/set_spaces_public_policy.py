"""
Set a public-read bucket policy on a DigitalOcean Space using boto3.

Requirements
 - Environment variables (already used by the Django app):
     AWS_ACCESS_KEY_ID
     AWS_SECRET_ACCESS_KEY
     AWS_STORAGE_BUCKET_NAME (bucket/space name)
     AWS_S3_REGION_NAME (e.g. "fra1")
     AWS_S3_ENDPOINT_URL (e.g. "https://fra1.digitaloceanspaces.com")

Usage
 - From the project root (where manage.py is), run:
     python scripts/set_spaces_public_policy.py

Notes
 - This does NOT expose bucket listing, only object GET (public read of files).
 - If a policy already exists, it will be overwritten with a simple public-read statement.
 - Designed for DigitalOcean Spaces (S3-compatible endpoint).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict


def env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None or not str(val).strip():
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return val


def make_policy(bucket: str) -> Dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicRead",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }
        ],
    }


def main() -> int:
    # Read env configuration
    bucket = env("AWS_STORAGE_BUCKET_NAME")
    region = env("AWS_S3_REGION_NAME")
    endpoint = os.environ.get("AWS_S3_ENDPOINT_URL") or f"https://{region}.digitaloceanspaces.com"
    access_key = env("AWS_ACCESS_KEY_ID")
    secret_key = env("AWS_SECRET_ACCESS_KEY")

    # Lazy import to avoid importing boto3 if not installed in some environments
    try:
        import boto3  # type: ignore
    except Exception as exc:  # pragma: no cover
        print("boto3 is required. Ensure django-storages[boto3] is installed.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 3

    session = boto3.session.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    s3 = session.client("s3", endpoint_url=endpoint)

    policy = make_policy(bucket)
    try:
        s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    except Exception as exc:
        print("Failed to put bucket policy:", exc, file=sys.stderr)
        return 4

    # Fetch back and print for confirmation
    try:
        resp = s3.get_bucket_policy(Bucket=bucket)
        current = resp.get("Policy")
        print("Applied bucket policy on:", bucket)
        print(current)
    except Exception as exc:
        print("Policy applied, but could not read back policy:", exc, file=sys.stderr)
        return 0

    # Also print a sample public URL format for convenience
    sample_key = "health/hello.txt"
    public_url = f"https://{bucket}.{region}.digitaloceanspaces.com/{sample_key}"
    print("Example public object URL format:")
    print(public_url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
