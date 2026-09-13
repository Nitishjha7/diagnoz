from pathlib import Path

import boto3

from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def ensure_bucket(s3_client) -> None:
    existing = {b["Name"] for b in s3_client.list_buckets().get("Buckets", [])}
    if settings.S3_BUCKET not in existing:
        s3_client.create_bucket(Bucket=settings.S3_BUCKET)


def upload_directory(s3_client, local_dir: Path, s3_prefix: str) -> None:
    ensure_bucket(s3_client)
    for file_path in local_dir.rglob("*"):
        if file_path.is_file():
            key = f"{s3_prefix}/{file_path.relative_to(local_dir).as_posix()}"
            s3_client.upload_file(str(file_path), settings.S3_BUCKET, key)


def upload_file(s3_client, local_path: Path, s3_key: str) -> None:
    ensure_bucket(s3_client)
    s3_client.upload_file(str(local_path), settings.S3_BUCKET, s3_key)
