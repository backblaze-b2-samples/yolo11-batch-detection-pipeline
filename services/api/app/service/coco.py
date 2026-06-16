"""Pure COCO-format assembly from plain `Detection` models.

No SDK imports — this module only reshapes our own Pydantic models into the
COCO object-detection JSON schema (images[] / annotations[] / categories[]).
Used for both per-image COCO files and the combined `instances.json` dataset.
"""

import json
from datetime import UTC, datetime

from app.types import Detection, ImageResult

_INFO = {
    "description": "YOLO11 Batch Detection Pipeline export",
    "version": "1.0",
}


def _categories(class_by_id: dict[int, str]) -> list[dict]:
    return [
        {"id": cid, "name": name, "supercategory": "object"}
        for cid, name in sorted(class_by_id.items())
    ]


def per_image_coco(image: ImageResult, image_id: int = 1) -> bytes:
    """COCO JSON for a single image's detections, as UTF-8 bytes."""
    class_by_id: dict[int, str] = {}
    annotations: list[dict] = []
    for ann_id, det in enumerate(image.detections, start=1):
        class_by_id[det.category_id] = det.class_name
        annotations.append(_annotation(ann_id, image_id, det))
    doc = {
        "info": {**_INFO, "date_created": datetime.now(UTC).isoformat()},
        "images": [_image_entry(image_id, image)],
        "annotations": annotations,
        "categories": _categories(class_by_id),
    }
    return json.dumps(doc, indent=2).encode("utf-8")


def combined_coco(images: list[ImageResult]) -> bytes:
    """Combined COCO `instances.json` across every image in a run."""
    class_by_id: dict[int, str] = {}
    image_entries: list[dict] = []
    annotations: list[dict] = []
    ann_id = 1
    for image_id, image in enumerate(images, start=1):
        image_entries.append(_image_entry(image_id, image))
        for det in image.detections:
            class_by_id[det.category_id] = det.class_name
            annotations.append(_annotation(ann_id, image_id, det))
            ann_id += 1
    doc = {
        "info": {**_INFO, "date_created": datetime.now(UTC).isoformat()},
        "images": image_entries,
        "annotations": annotations,
        "categories": _categories(class_by_id),
    }
    return json.dumps(doc, indent=2).encode("utf-8")


def _image_entry(image_id: int, image: ImageResult) -> dict:
    return {
        "id": image_id,
        "file_name": image.source_key,
        "width": image.width,
        "height": image.height,
    }


def _annotation(ann_id: int, image_id: int, det: Detection) -> dict:
    _x, _y, w, h = det.bbox
    return {
        "id": ann_id,
        "image_id": image_id,
        "category_id": det.category_id,
        "category_name": det.class_name,
        "bbox": det.bbox,
        "area": round(w * h, 2),
        "score": det.score,
        "iscrowd": 0,
    }
