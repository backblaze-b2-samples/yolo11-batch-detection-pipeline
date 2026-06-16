"""Pure COCO-assembly tests (no SDK, no B2)."""

import json

from app.service import coco
from app.types import Detection, ImageResult


def _image(stem: str, dets: list[Detection]) -> ImageResult:
    return ImageResult(
        stem=stem,
        source_key=f"yolo11-batch-detection-pipeline/source/{stem}.jpg",
        width=640,
        height=480,
        detections=dets,
    )


def test_per_image_coco_shape():
    img = _image(
        "cat",
        [Detection(category_id=15, class_name="cat", score=0.9, bbox=[10, 20, 100, 120])],
    )
    doc = json.loads(coco.per_image_coco(img))
    assert len(doc["images"]) == 1
    assert len(doc["annotations"]) == 1
    assert doc["annotations"][0]["bbox"] == [10, 20, 100, 120]
    assert doc["annotations"][0]["area"] == 12000.0
    assert doc["categories"][0]["name"] == "cat"


def test_combined_coco_deduplicates_categories_and_increments_ids():
    a = _image(
        "a",
        [Detection(category_id=0, class_name="person", score=0.8, bbox=[0, 0, 10, 10])],
    )
    b = _image(
        "b",
        [
            Detection(category_id=0, class_name="person", score=0.7, bbox=[1, 1, 5, 5]),
            Detection(category_id=2, class_name="car", score=0.6, bbox=[2, 2, 8, 8]),
        ],
    )
    doc = json.loads(coco.combined_coco([a, b]))
    assert len(doc["images"]) == 2
    assert len(doc["annotations"]) == 3
    assert {c["name"] for c in doc["categories"]} == {"person", "car"}
    # image_ids are 1-based and distinct
    assert {img["id"] for img in doc["images"]} == {1, 2}
    assert {ann["id"] for ann in doc["annotations"]} == {1, 2, 3}
