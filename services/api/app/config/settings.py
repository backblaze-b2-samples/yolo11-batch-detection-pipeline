from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible) ---
    b2_endpoint: str = "https://s3.us-west-004.backblazeb2.com"
    b2_region: str = "us-west-004"
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits. Images and short videos are accepted as source media;
    # allow up to 200MB by default.
    max_file_size: int = 200 * 1024 * 1024  # 200MB

    # Small durable counter for the /files browser's download stats. Point at
    # a persistent volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # --- YOLO11 batch-detection pipeline (Ultralytics) ---
    # Default pre-trained COCO weights. Runs locally with NO API key; the
    # Ultralytics engine auto-downloads weights on first use. A smaller id
    # (e.g. `yolo11n.pt`) is faster on CPU; `yolo11n-seg.pt` enables masks.
    detection_model: str = "yolo11n.pt"
    detection_seg_model: str = "yolo11n-seg.pt"
    # Server-side floor on confidence; the UI re-filters above this floor with
    # a client-side slider, so keep it low enough to retain raw detections.
    detection_min_confidence: float = 0.10
    # Sample every Nth frame for video sources to keep CPU runtime tractable.
    video_frame_stride: int = 30
    # Cap the number of source frames/images a single run processes.
    max_images_per_run: int = 200
    # Cap the number of instance crops written per image (highest score first).
    max_crops_per_image: int = 20

    # --- B2 prefix scoping ---
    # Every artifact this app writes lives under this prefix. The /runs
    # library lists only this prefix; /files browses the full bucket.
    run_prefix: str = "yolo11-batch-detection-pipeline/"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @property
    def source_prefix(self) -> str:
        """Default B2 prefix that /upload targets and new runs read from."""
        return f"{self.run_prefix}source/"


settings = Settings()
