"""Batch-detection pipeline orchestrator.

Runs in a FastAPI BackgroundTask. Stages, emitted in order so a polling client
observes every state:
  LISTING -> DETECTING -> ANNOTATING -> CROPPING -> READY
Status is persisted to the run's manifest.json on B2 after each stage. It never
raises — failures are recorded on the manifest as status=FAILED.

Each stage wraps its real corresponding work over the whole batch:
  LISTING     enumerate source media under the chosen prefix
  DETECTING   run YOLO11 inference on every frame (the heavy pass)
  ANNOTATING  write annotated frames + per-image COCO JSON to B2
  CROPPING    write class-organized instance crops to B2
  READY       write the combined COCO `instances.json` dataset, then finish

The orchestrator owns no CV types: it delegates decode/detect/annotate/crop to
`repo` adapters (which confine `ultralytics`/`cv2`/`numpy`) and reasons only
over plain `Run` / `ImageResult` / `Detection` models. COCO assembly is pure
(`service.coco`). To keep memory bounded across a large batch, decoded frames
are spilled to the run's temp dir during DETECTING and reloaded in CROPPING
rather than held in memory.
"""

import logging
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.repo import annotate, detection, media
from app.repo import run_store as store
from app.service import coco
from app.types import ImageResult, Run, RunStatus

logger = logging.getLogger(__name__)


@dataclass
class _Pending:
    """In-flight per-frame state carried across pipeline stages.

    `frame_path` points at the decoded BGR frame spilled to the run's temp dir
    so CROPPING can reload it without keeping every frame in memory.
    """

    image: ImageResult
    annotated_jpeg: bytes
    frame_path: Path
    ordered_bboxes: list[list[float]] = field(default_factory=list)
    ordered_classes: list[str] = field(default_factory=list)


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

    with tempfile.TemporaryDirectory(prefix=f"yolo-{run.id}-") as tmp:
        tmp_path = Path(tmp)

        # --- DETECTING: run YOLO11 inference on every frame (heavy pass) ---
        _touch(run, RunStatus.DETECTING)
        pending: list[_Pending] = []
        for key, _size in sources:
            pending.extend(_detect_source(run, key, model_name, tmp_path))
            run.images = [p.image for p in pending]
            run.image_count = len(pending)
            run.detection_count = sum(len(p.image.detections) for p in pending)
            run.class_counts = _class_counts(run.images)
            store.write_manifest(run)

        # --- ANNOTATING: write annotated frames + per-image COCO to B2 ---
        _touch(run, RunStatus.ANNOTATING)
        for i, p in enumerate(pending, start=1):
            _persist_annotations(run, p)
            if i % 10 == 0 or i == len(pending):
                store.write_manifest(run)

        # --- CROPPING: write class-organized instance crops to B2 ---
        _touch(run, RunStatus.CROPPING)
        for i, p in enumerate(pending, start=1):
            _persist_crops(run, p)
            run.crop_count = sum(len(pp.image.crop_keys) for pp in pending)
            if i % 10 == 0 or i == len(pending):
                store.write_manifest(run)

        results = [p.image for p in pending]

    # --- READY: write the combined COCO `instances.json` dataset ---
    instances = coco.combined_coco(results)
    ikey = store.instances_key(run.id)
    run.derived_bytes += store.put_bytes(ikey, instances, "application/json")
    run.instances_key = ikey
    store.write_manifest(run)

    _touch(run, RunStatus.READY)


def _detect_source(
    run: Run, key: str, model_name: str, tmp: Path
) -> list[_Pending]:
    """Decode + detect one source object. A still image yields one frame; a
    video yields one per sampled frame. Inference runs here (DETECTING)."""
    if media.is_video(key):
        local = tmp / Path(key).name
        store.download_to(key, str(local))
        out: list[_Pending] = []
        for fidx, t, frame in media.sample_video_frames(
            str(local), settings.video_frame_stride, settings.max_images_per_run
        ):
            stem = f"{Path(key).stem}-f{fidx:06d}"
            out.append(_detect_one(run, key, stem, frame, model_name, tmp, frame_t=t))
        return out
    raw = store.get_bytes(key)
    if raw is None:
        logger.warning("Source vanished mid-run: %s", key)
        return []
    frame = media.decode_image(raw)
    stem = Path(key).stem
    return [_detect_one(run, key, stem, frame, model_name, tmp)]


def _detect_one(
    run: Run, source_key: str, stem: str, frame, model_name: str, tmp: Path, frame_t=None
) -> _Pending:
    """Run detection on a single decoded frame; spill the frame to disk and
    keep the annotated render for the ANNOTATING/CROPPING stages."""
    width, height = media.frame_size(frame)
    detections, annotated_jpeg = annotate.detect_and_annotate(frame, run.task, model_name)

    image = ImageResult(
        stem=stem,
        source_key=source_key,
        width=width,
        height=height,
        detections=detections,
        frame_t=frame_t,
    )

    frame_path = tmp / f"{stem}.frame.npy"
    media.save_frame(frame, str(frame_path))

    ordered = sorted(detections, key=lambda d: d.score, reverse=True)
    return _Pending(
        image=image,
        annotated_jpeg=annotated_jpeg,
        frame_path=frame_path,
        ordered_bboxes=[d.bbox for d in ordered],
        ordered_classes=[d.class_name for d in ordered],
    )


def _persist_annotations(run: Run, p: _Pending) -> None:
    """ANNOTATING work for one frame: upload the annotated JPEG + per-image COCO."""
    akey = store.annotated_key(run.id, p.image.stem)
    run.derived_bytes += store.put_bytes(akey, p.annotated_jpeg, "image/jpeg")
    p.image.annotated_key = akey

    ckey = store.coco_key(run.id, p.image.stem)
    run.derived_bytes += store.put_bytes(
        ckey, coco.per_image_coco(p.image), "application/json"
    )
    p.image.coco_key = ckey


def _persist_crops(run: Run, p: _Pending) -> None:
    """CROPPING work for one frame: reload the spilled frame, crop class-ordered
    instances (highest score first), upload each crop."""
    if not p.ordered_bboxes:
        return
    frame = media.load_frame(str(p.frame_path))
    crops = media.crop_instances(frame, p.ordered_bboxes)
    for n, (class_name, crop) in enumerate(
        zip(p.ordered_classes, crops, strict=False)
    ):
        kkey = store.crop_key(run.id, class_name, p.image.stem, n)
        run.derived_bytes += store.put_bytes(kkey, crop, "image/jpeg")
        p.image.crop_keys.append(kkey)


def _class_counts(results: list[ImageResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in results:
        for d in r.detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
