from pathlib import Path
from typing import BinaryIO, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app


class UploadError(RuntimeError):
    """Raised when a video upload fails."""


def _get_s3_client():
    """Instantiate an S3 client using any configured region override."""
    region = current_app.config.get("AWS_REGION")
    return boto3.client("s3", region_name=region)


def upload_video_to_s3(file_obj: BinaryIO, key: str, content_type: Optional[str] = None) -> Dict[str, Optional[str]]:
    bucket = current_app.config.get("AWS_S3_BUCKET")
    if not bucket:
        raise UploadError("AWS_S3_BUCKET is not configured.")

    client = _get_s3_client()
    extra_args = {"ContentType": content_type} if content_type else None

    try:
        if extra_args:
            client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)
        else:
            client.upload_fileobj(file_obj, bucket, key)
    except (BotoCoreError, ClientError) as exc:
        raise UploadError("Failed to upload video to S3") from exc

    return {
        "bucket": bucket,
        "key": key,
        "region": client.meta.region_name or current_app.config.get("AWS_REGION"),
    }


def build_video_url(s3_metadata: Dict[str, Optional[str]]) -> str:
    template = current_app.config.get("STREAMING_TEMPLATE")
    if template:
        name = Path(s3_metadata["key"]).stem
        return template.format(name=name, key=s3_metadata["key"])

    region = s3_metadata.get("region")
    bucket = s3_metadata["bucket"]
    key = s3_metadata["key"]

    if region in (None, "us-east-1"):
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
