"""Dashboard aggregation for the batch-detection pipeline.

Scans this app's run manifests and rolls them up into headline metrics: runs,
images processed, detections, crops, distinct classes, and the source-vs-derived
B2 storage footprint multiplier (the strategic B2 story) + a recent-runs list
with live status.
"""

from app.repo import run_store as store
from app.service.runs import _to_summary
from app.types import RunStats, RunSummary
from app.types.formatting import humanize_bytes

RECENT_LIMIT = 8


def get_run_stats() -> RunStats:
    runs = 0
    images_processed = 0
    detections = 0
    crops_generated = 0
    source_bytes = 0
    derived_bytes = 0
    classes: set[str] = set()
    recent: list[RunSummary] = []

    for rid in store.list_run_ids():
        run = store.read_manifest(rid)
        if run is None:
            continue
        runs += 1
        images_processed += run.image_count
        detections += run.detection_count
        crops_generated += run.crop_count
        source_bytes += run.source_bytes
        derived_bytes += run.derived_bytes
        classes.update(run.class_counts.keys())
        if len(recent) < RECENT_LIMIT:
            recent.append(_to_summary(run))

    multiplier = round(derived_bytes / source_bytes, 2) if source_bytes else 0.0

    return RunStats(
        runs=runs,
        images_processed=images_processed,
        detections=detections,
        crops_generated=crops_generated,
        distinct_classes=len(classes),
        source_bytes=source_bytes,
        source_bytes_human=humanize_bytes(source_bytes),
        derived_bytes=derived_bytes,
        derived_bytes_human=humanize_bytes(derived_bytes),
        footprint_multiplier=multiplier,
        recent=recent,
    )
