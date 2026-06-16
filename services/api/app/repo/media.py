"""Image/video decode, frame sampling, and instance cropping.

OpenCV (`cv2`) and `numpy` are external dependencies, so per the repo invariant
they live here, not in the service layer. Everything is imported lazily so the
module stays importable for structural tests without the CV runtime installed.

Callers in repo/ pass and receive decoded BGR frames (numpy arrays); the only
things that cross back into the service layer are JPEG *bytes* and plain ints.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


class MediaError(RuntimeError):
    """Raised when an image/video cannot be decoded."""


def is_video(key: str) -> bool:
    return key.lower().endswith((".mp4", ".mov"))


def decode_image(data: bytes):
    """Decode image bytes to a BGR frame (numpy array). Raises MediaError."""
    import cv2
    import numpy as np

    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise MediaError("Could not decode image bytes")
    return frame


def sample_video_frames(path: str, stride: int, max_frames: int):
    """Yield (frame_index, timestamp_seconds, BGR frame) every `stride` frames.

    A generator so a long video never materializes every frame in memory.
    """
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise MediaError(f"Could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    idx = 0
    yielded = 0
    try:
        while yielded < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % stride == 0:
                yield idx, round(idx / fps, 3), frame
                yielded += 1
            idx += 1
    finally:
        cap.release()


def frame_size(frame) -> tuple[int, int]:
    """(width, height) of a BGR frame."""
    h, w = frame.shape[:2]
    return int(w), int(h)


def encode_jpeg(frame, quality: int = 90) -> bytes:
    """Encode a BGR frame to JPEG bytes. Raises MediaError on failure."""
    import cv2

    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise MediaError("JPEG encode failed")
    return buf.tobytes()


def crop_instances(frame, boxes: list[list[float]]) -> list[bytes]:
    """Crop each `[x, y, w, h]` (absolute px) region from `frame` and return
    JPEG bytes. Boxes are clamped to the frame; degenerate crops are skipped.
    Capped at `settings.max_crops_per_image`.
    """
    h, w = frame.shape[:2]
    crops: list[bytes] = []
    for x, y, bw, bh in boxes[: settings.max_crops_per_image]:
        x1 = max(0, int(x))
        y1 = max(0, int(y))
        x2 = min(w, int(x + bw))
        y2 = min(h, int(y + bh))
        if x2 <= x1 or y2 <= y1:
            continue
        crops.append(encode_jpeg(frame[y1:y2, x1:x2]))
    return crops
