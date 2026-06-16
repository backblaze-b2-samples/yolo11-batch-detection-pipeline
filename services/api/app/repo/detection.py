"""Ultralytics YOLO11 adapter — the ONLY place the detection model runs.

Pre-trained COCO weights (default `yolo11n.pt`) run locally with NO API key;
the Ultralytics engine auto-downloads weights on first use. `ultralytics`,
`cv2`, and `numpy` are heavy/optional at import time, so they are imported
lazily inside the functions — this keeps the module importable for structural
tests without the CV runtime installed.

The public surface returns plain `Detection` models (and JPEG *bytes* for
annotated frames / crops), never an Ultralytics `Results` or a numpy array, so
the service layer stays decoupled from every CV type.
"""

import functools
import logging

from app.config import settings
from app.types import Detection, DetectionTask

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=2)
def _get_model(model_name: str):
    """Load a YOLO11 model once (weights auto-download on first call)."""
    from ultralytics import YOLO

    logger.info("Loading YOLO11 model: %s", model_name)
    return YOLO(model_name)


def model_for(task: DetectionTask) -> str:
    """Resolve the configured weights file for a task."""
    if task == DetectionTask.SEGMENT:
        return settings.detection_seg_model
    return settings.detection_model


def _to_detections(result, task: DetectionTask) -> list[Detection]:
    """Convert an Ultralytics `Results` to plain `Detection` models.

    bbox is emitted as COCO `[x, y, w, h]` in absolute pixels.
    """
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []
    names = result.names
    has_masks = task == DetectionTask.SEGMENT and getattr(result, "masks", None) is not None
    xyxy = boxes.xyxy.tolist()
    confs = boxes.conf.tolist()
    clss = boxes.cls.tolist()
    out: list[Detection] = []
    for (x1, y1, x2, y2), score, cls in zip(xyxy, confs, clss, strict=False):
        cid = int(cls)
        out.append(
            Detection(
                category_id=cid,
                class_name=str(names.get(cid, cid)),
                score=round(float(score), 4),
                bbox=[
                    round(float(x1), 2),
                    round(float(y1), 2),
                    round(float(x2 - x1), 2),
                    round(float(y2 - y1), 2),
                ],
                has_mask=has_masks,
            )
        )
    return out


def detect_frame(frame, task: DetectionTask, model_name: str) -> list[Detection]:
    """Run YOLO11 on a single BGR frame (numpy array) and return plain
    `Detection` models. The annotated render is produced separately by
    `annotate.render` so it can reuse the same inference pass via `detect_and_render`.
    """
    model = _get_model(model_name)
    result = model(frame, conf=settings.detection_min_confidence, verbose=False)[0]
    return _to_detections(result, task)


def detect_and_render(frame, task: DetectionTask, model_name: str):
    """Run inference once and return (detections, annotated_bgr_frame).

    The annotated frame is a numpy array (kept inside repo/); callers in repo/
    encode it to JPEG bytes via `media.encode_jpeg`.
    """
    model = _get_model(model_name)
    result = model(frame, conf=settings.detection_min_confidence, verbose=False)[0]
    detections = _to_detections(result, task)
    annotated = result.plot()  # BGR ndarray with boxes/labels (+ masks if seg)
    return detections, annotated
