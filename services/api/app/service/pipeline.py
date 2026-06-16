"""Batch-detection pipeline orchestrator.

Runs in a FastAPI BackgroundTask. Stages:
  LISTING -> DETECTING -> ANNOTATING -> CROPPING -> READY
Status is persisted to the run's manifest.json on B2 after each stage so the
frontend can poll live progress. It never raises — failures are recorded on the
manifest as status=FAILED.

The orchestrator owns no CV types: it delegates decode/detect/annotate/crop to
`repo` adapters (which confine `ultralytics`/`cv2`/`numpy`) and reasons only
over plain `Run` / `ImageResult` / `Detection` models. COCO assembly is pure
(`service.coco`).
"""

import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.repo import annotate, detection, media
from app.repo import run_store as store
from app.service import coco
from app.types import ImageResult, Run, RunStatus

logger = logging.getLogger(__name__)


def _touch(run: Run, status: RunStatus) -> None:
    run.status = status
    run.updated_at = datetime.now(UTC)
    store.write_manifest(run)
    logger.info("run=%s status=%s", run.id, status.value)


def run_pipeline(run_id: str) -> None:
    """Entry point for the BackgroundTask. Never raises — failures are recorded
    on the manifest as status=FAILED."""
    run = store.read_manifest(run_id)
    if run is None:
        logger.error("run_pipeline: no manifest for %s", run_id)
        return
    try:
        _run(run)
    except Exception as e:  # pipeline must never crash the worker
        logger.exception("Pipeline failed for %s", run_id)
        run.error = str(e)[:500]
        _touch(run, RunStatus.FAILED)


def _run(run: Run) -> None:
    model_name = detection.model_for(run.task)

    # --- LISTING: enumerate source media under the chosen prefix ---
    _touch(run, RunStatus.LISTING)
    sources = store.list_source_media(run.source_prefix, settings.max_images_per_run)
    run.source_bytes = sum(size for _, size in sources)
    store.write_manifest(run)
    if not sources:
        run.error = f"No image/video media found under '{run.source_prefix}'."
        _touch(run, RunStatus.FAILED)
        return

    # --- DETECTING + ANNOTATING + CROPPING (per image/frame) ---
    _touch(run, RunStatus.DETECTING)
    results: list[ImageResult] = []
    with tempfile.TemporaryDirectory(prefix=f"yolo-{run.id}-") as tmp:
        for key, _size in sources:
            results.extend(_process_source(run, key, model_name, Path(tmp)))
            run.images = results
            run.image_count = len(results)
            run.detection_count = sum(len(r.detections) for r in results)
            run.crop_count = sum(len(r.crop_keys) for r in results)
            run.class_counts = _class_counts(results)
            store.write_manifest(run)

    # --- Combined COCO dataset (export artifact) ---
    _touch(run, RunStatus.CROPPING)  # final write phase
    instances = coco.combined_coco(results)
    ikey = store.instances_key(run.id)
    run.derived_bytes += store.put_bytes(ikey, instances, "application/json")
    run.instances_key = ikey
    store.write_manifest(run)

    _touch(run, RunStatus.READY)


def _process_source(run: Run, key: str, model_name: str, tmp: Path) -> list[ImageResult]:
    """Detect+annotate+crop one source object. A still image yields one
    ImageResult; a video yields one per sampled frame."""
    if media.is_video(key):
        local = tmp / Path(key).name
        store.download_to(key, str(local))
        out: list[ImageResult] = []
        for fidx, t, frame in media.sample_video_frames(
            str(local), settings.video_frame_stride, settings.max_images_per_run
        ):
            stem = f"{Path(key).stem}-f{fidx:06d}"
            out.append(_detect_one(run, key, stem, frame, model_name, frame_t=t))
        return out
    raw = store.get_bytes(key)
    if raw is None:
        logger.warning("Source vanished mid-run: %s", key)
        return []
    frame = media.decode_image(raw)
    stem = Path(key).stem
    return [_detect_one(run, key, stem, frame, model_name)]


def _detect_one(
    run: Run, source_key: str, stem: str, frame, model_name: str, frame_t=None
) -> ImageResult:
    """Run detection on a single decoded frame and persist its artifacts."""
    width, height = media.frame_size(frame)
    detections, annotated_jpeg = annotate.detect_and_annotate(
        frame, run.task, model_name
    )

    image = ImageResult(
        stem=stem,
        source_key=source_key,
        width=width,
        height=height,
        detections=detections,
        frame_t=frame_t,
    )

    # Annotated frame
    akey = store.annotated_key(run.id, stem)
    run.derived_bytes += store.put_bytes(akey, annotated_jpeg, "image/jpeg")
    image.annotated_key = akey

    # Per-image COCO JSON
    ckey = store.coco_key(run.id, stem)
    run.derived_bytes += store.put_bytes(
        ckey, coco.per_image_coco(image), "application/json"
    )
    image.coco_key = ckey

    # Class-organized instance crops (highest score first)
    ordered = sorted(detections, key=lambda d: d.score, reverse=True)
    crops = media.crop_instances(frame, [d.bbox for d in ordered])
    for n, (det, crop) in enumerate(zip(ordered, crops, strict=False)):
        kkey = store.crop_key(run.id, det.class_name, stem, n)
        run.derived_bytes += store.put_bytes(kkey, crop, "image/jpeg")
        image.crop_keys.append(kkey)

    return image


def _class_counts(results: list[ImageResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in results:
        for d in r.detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
