"""B2 (S3) data access for the YOLO11 batch-detection pipeline.

All keys live under `settings.run_prefix`. The manifest.json per run is the
single source of truth (status + image index + aggregates); there is no
database. boto3 stays confined to this layer.
"""

import logging

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.types import Run

logger = logging.getLogger(__name__)


# ----- Key builders (scoped to settings.run_prefix) -----


def _base(run_id: str) -> str:
    return f"{settings.run_prefix}runs/{run_id}/"


def manifest_key(run_id: str) -> str:
    return f"{_base(run_id)}manifest.json"


def annotated_key(run_id: str, stem: str) -> str:
    return f"{_base(run_id)}annotated/{stem}.jpg"


def coco_key(run_id: str, stem: str) -> str:
    return f"{_base(run_id)}coco/{stem}.json"


def instances_key(run_id: str) -> str:
    return f"{_base(run_id)}coco/instances.json"


def crop_key(run_id: str, class_name: str, stem: str, n: int) -> str:
    safe_class = "".join(c if c.isalnum() or c in "-_" else "_" for c in class_name)
    return f"{_base(run_id)}crops/{safe_class}/{stem}-{n}.jpg"


# ----- Object IO -----


def put_bytes(key: str, data: bytes, content_type: str) -> int:
    """Upload raw bytes to B2; returns byte count. Raises RuntimeError on fail."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    return len(data)


def get_bytes(key: str) -> bytes | None:
    """Download an object's bytes. Returns None if it doesn't exist."""
    client = get_s3_client()
    try:
        resp = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return resp["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e


def download_to(key: str, dest_path: str) -> None:
    """Download an object to a local path. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.download_file(settings.b2_bucket_name, key, dest_path)
    except ClientError as e:
        raise RuntimeError(f"B2 download failed for '{key}': {e}") from e


def presign_get(key: str, expires_in: int = 3600) -> str:
    """Presigned GET URL for inline preview (no attachment disposition)."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def presign_download(key: str, filename: str, expires_in: int = 600) -> str:
    """Presigned GET URL that downloads as an attachment (COCO export)."""
    client = get_s3_client()
    params = {
        "Bucket": settings.b2_bucket_name,
        "Key": key,
        "ResponseContentDisposition": f'attachment; filename="{filename}"',
    }
    try:
        return client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


# ----- Source listing (scoped to a run's chosen source prefix) -----

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
VIDEO_EXTS = (".mp4", ".mov")


def list_source_media(prefix: str, limit: int) -> list[tuple[str, int]]:
    """List (key, size_bytes) of image/video objects under `prefix`, capped."""
    client = get_s3_client()
    found: list[tuple[str, int]] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                low = key.lower()
                if low.endswith(IMAGE_EXTS) or low.endswith(VIDEO_EXTS):
                    found.append((key, obj["Size"]))
                    if len(found) >= limit:
                        return found
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 source list failed for '{prefix}': {e}") from e
    return found


# ----- Manifest (status + image index + aggregates) -----


def write_manifest(run: Run) -> None:
    put_bytes(
        manifest_key(run.id),
        run.model_dump_json(indent=2).encode("utf-8"),
        "application/json",
    )


def read_manifest(run_id: str) -> Run | None:
    raw = get_bytes(manifest_key(run_id))
    if raw is None:
        return None
    try:
        return Run.model_validate_json(raw)
    except ValueError:
        logger.warning("Corrupt manifest for run %s", run_id)
        return None


# ----- Scoped listing & deletion -----


def list_run_ids() -> list[str]:
    """List every run id under this app's prefix (one per manifest.json),
    newest objects first by LastModified."""
    client = get_s3_client()
    prefix = f"{settings.run_prefix}runs/"
    found: list[tuple[str, object]] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/manifest.json"):
                    rid = key[len(prefix):].split("/", 1)[0]
                    found.append((rid, obj["LastModified"]))
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed: {e}") from e
    found.sort(key=lambda t: t[1], reverse=True)
    return [rid for rid, _ in found]


def delete_run_prefix(run_id: str) -> int:
    """Delete a single run and every derived artifact under its prefix ONLY.

    Scoped to `…/runs/{run_id}/` — never touches other runs, the source corpus,
    or other apps' prefixes. Returns the number of objects deleted.
    """
    client = get_s3_client()
    prefix = _base(run_id)
    deleted = 0
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            objects = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
            if objects:
                client.delete_objects(
                    Bucket=settings.b2_bucket_name,
                    Delete={"Objects": objects},
                )
                deleted += len(objects)
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 scoped delete failed for '{prefix}': {e}") from e
    return deleted


__all__ = [
    "annotated_key",
    "coco_key",
    "crop_key",
    "delete_run_prefix",
    "download_to",
    "get_bytes",
    "instances_key",
    "list_run_ids",
    "list_source_media",
    "manifest_key",
    "presign_download",
    "presign_get",
    "put_bytes",
    "read_manifest",
    "write_manifest",
]
