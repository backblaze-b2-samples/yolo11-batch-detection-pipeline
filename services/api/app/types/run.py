"""Domain models for the YOLO11 batch-detection pipeline.

Every model here is a plain Pydantic model — no CV-SDK types leak into them.
A run's `manifest.json` on B2 (a serialized `Run`) is the single source of
truth: there is no database and no queue.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class RunStatus(StrEnum):
    """Lifecycle of a batch run, persisted in the run's manifest.json.

    The frontend polls while any run is in a non-terminal state and stops once
    every run reaches `ready` or `failed`.
    """

    QUEUED = "queued"
    LISTING = "listing"
    DETECTING = "detecting"
    ANNOTATING = "annotating"
    CROPPING = "cropping"
    READY = "ready"
    FAILED = "failed"


# States from which the pipeline is still working — the UI polls in these.
ACTIVE_RUN_STATUSES = {
    RunStatus.QUEUED,
    RunStatus.LISTING,
    RunStatus.DETECTING,
    RunStatus.ANNOTATING,
    RunStatus.CROPPING,
}


class DetectionTask(StrEnum):
    """Which YOLO11 head to run."""

    DETECT = "detect"
    SEGMENT = "segment"


class Detection(BaseModel):
    """A single detected instance on one image/frame.

    `bbox` is `[x, y, w, h]` in absolute pixels (COCO convention). `has_mask`
    records whether a segmentation mask was produced (segment task) without
    leaking the raw mask array into the manifest.
    """

    category_id: int
    class_name: str
    score: float
    bbox: list[float]
    has_mask: bool = False


class ImageResult(BaseModel):
    """Detections + derived-artifact keys for one source image/frame."""

    stem: str
    source_key: str
    width: int
    height: int
    detections: list[Detection] = []
    annotated_key: str | None = None
    coco_key: str | None = None
    crop_keys: list[str] = []
    # For video sources: the frame timestamp (seconds). None for still images.
    frame_t: float | None = None


class Run(BaseModel):
    """A batch detection run and the state of its pipeline.

    Serialized to `…/runs/{id}/manifest.json` on B2 — the manifest is the
    single source of truth. There is no database.
    """

    id: str
    name: str
    source_prefix: str
    task: DetectionTask = DetectionTask.DETECT
    model: str
    min_confidence: float
    status: RunStatus = RunStatus.QUEUED
    error: str | None = None
    # Pipeline outputs (aggregated for fast list/dashboard reads).
    images: list[ImageResult] = []
    image_count: int = 0
    detection_count: int = 0
    crop_count: int = 0
    class_counts: dict[str, int] = {}
    source_bytes: int = 0
    derived_bytes: int = 0
    instances_key: str | None = None
    created_at: datetime
    updated_at: datetime


class RunSummary(BaseModel):
    """Lightweight projection for the Runs Library list view."""

    id: str
    name: str
    status: RunStatus
    task: DetectionTask
    image_count: int
    detection_count: int
    crop_count: int
    thumb_url: str | None = None
    created_at: datetime
    updated_at: datetime


class RunStats(BaseModel):
    """Dashboard aggregates across every run under this app's prefix."""

    runs: int
    images_processed: int
    detections: int
    crops_generated: int
    distinct_classes: int
    source_bytes: int
    source_bytes_human: str
    derived_bytes: int
    derived_bytes_human: str
    footprint_multiplier: float
    recent: list[RunSummary]
