"""Annotation adapter — turns one inference pass into a drawn, encoded frame.

YOLO11's `Results.plot()` draws boxes, labels, and (for the segment task) masks
onto a copy of the frame. This module composes `detection` (the model) with
`media` (JPEG encoding) so the service layer gets a single high-level call that
returns plain `Detection` models plus annotated-JPEG *bytes* — no CV types leak
upward. Imports stay inside `detection`/`media`, which are lazy.
"""

from app.repo import detection, media
from app.types import Detection, DetectionTask


def detect_and_annotate(
    frame, task: DetectionTask, model_name: str
) -> tuple[list[Detection], bytes]:
    """Run YOLO11 once on a BGR frame and return (detections, annotated JPEG).

    The annotated JPEG carries boxes + class/score labels (and segmentation
    masks when `task == SEGMENT`), produced by the model's own renderer.
    """
    detections, annotated = detection.detect_and_render(frame, task, model_name)
    return detections, media.encode_jpeg(annotated)
