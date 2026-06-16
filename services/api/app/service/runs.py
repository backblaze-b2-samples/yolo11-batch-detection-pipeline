"""Run register / list / get / delete + detection-result and export reads.

The pipeline itself lives in pipeline.py; this module is the read/write surface
the runtime layer talks to. All deletes are scoped to a single run's prefix —
they never touch other runs, the source corpus, or other apps' data.
"""

import logging
import re
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.repo import run_store as store
from app.types import (
    DetectionTask,
    ImageResult,
    Run,
    RunStatus,
    RunSummary,
)

logger = logging.getLogger(__name__)

_ID_RE = re.compile(r"^[a-f0-9]{32}$")


class RunError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class RunNotFound(Exception):
    def __init__(self, detail: str = "Run not found"):
        self.detail = detail
        super().__init__(detail)


def _validate_id(run_id: str) -> None:
    if not _ID_RE.match(run_id):
        raise RunError("Invalid run id")


def _normalize_prefix(prefix: str) -> str:
    """Default empty/blank source to this app's source/ prefix; reject keys
    that try to escape the bucket with traversal."""
    prefix = (prefix or "").strip().lstrip("/")
    if not prefix:
        return settings.source_prefix
    if ".." in prefix:
        raise RunError("Source prefix must not contain '..'")
    return prefix


def create_run(
    name: str, source_prefix: str, task: str, model: str | None, min_confidence: float
) -> Run:
    """Register a new run and write its initial manifest (status=queued). The
    caller kicks off the pipeline as a BackgroundTask."""
    try:
        task_enum = DetectionTask(task)
    except ValueError as e:
        raise RunError(f"Unknown task '{task}'. Use detect or segment.") from e

    norm_prefix = _normalize_prefix(source_prefix)
    conf = max(0.0, min(1.0, float(min_confidence)))
    resolved_model = (model or "").strip() or (
        settings.detection_seg_model
        if task_enum == DetectionTask.SEGMENT
        else settings.detection_model
    )

    run_id = uuid.uuid4().hex
    now = datetime.now(UTC)
    run = Run(
        id=run_id,
        name=(name or "").strip() or f"run-{run_id[:8]}",
        source_prefix=norm_prefix,
        task=task_enum,
        model=resolved_model,
        min_confidence=conf,
        status=RunStatus.QUEUED,
        created_at=now,
        updated_at=now,
    )
    store.write_manifest(run)
    logger.info("Created run %s (prefix=%s task=%s)", run_id, norm_prefix, task_enum)
    return run


def get_run(run_id: str) -> Run:
    _validate_id(run_id)
    run = store.read_manifest(run_id)
    if run is None:
        raise RunNotFound()
    return run


def list_runs() -> list[RunSummary]:
    summaries: list[RunSummary] = []
    for rid in store.list_run_ids():
        run = store.read_manifest(rid)
        if run is None:
            continue
        summaries.append(_to_summary(run))
    return summaries


def _to_summary(run: Run) -> RunSummary:
    thumb_url = None
    thumb_key = _first_annotated_key(run.images)
    if thumb_key:
        thumb_url = store.presign_get(thumb_key)
    return RunSummary(
        id=run.id,
        name=run.name,
        status=run.status,
        task=run.task,
        image_count=run.image_count,
        detection_count=run.detection_count,
        crop_count=run.crop_count,
        thumb_url=thumb_url,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _first_annotated_key(images: list[ImageResult]) -> str | None:
    for img in images:
        if img.annotated_key:
            return img.annotated_key
    return None


def detections_view(run_id: str) -> dict:
    """Per-image detections enriched with presigned annotated-frame and crop
    URLs, for client-side confidence-threshold browsing."""
    run = get_run(run_id)
    images = []
    for img in run.images:
        images.append(
            {
                "stem": img.stem,
                "source_key": img.source_key,
                "width": img.width,
                "height": img.height,
                "frame_t": img.frame_t,
                "annotated_url": store.presign_get(img.annotated_key)
                if img.annotated_key
                else None,
                "detections": [d.model_dump() for d in img.detections],
                "crop_urls": [store.presign_get(k) for k in img.crop_keys],
            }
        )
    return {
        "id": run.id,
        "name": run.name,
        "task": run.task,
        "min_confidence": run.min_confidence,
        "class_counts": run.class_counts,
        "images": images,
    }


def export_url(run_id: str) -> str:
    """Presigned download URL for the combined COCO instances.json dataset."""
    run = get_run(run_id)
    if not run.instances_key:
        raise RunNotFound("COCO dataset not ready for this run")
    return store.presign_download(run.instances_key, f"{run.name}-instances.json")


def delete_run(run_id: str) -> int:
    """Delete a run and ALL its derived artifacts — scoped to that run's prefix
    only. Returns the number of B2 objects removed."""
    _validate_id(run_id)
    if store.read_manifest(run_id) is None:
        raise RunNotFound()
    count = store.delete_run_prefix(run_id)
    logger.info("Deleted run %s (%d objects)", run_id, count)
    return count
