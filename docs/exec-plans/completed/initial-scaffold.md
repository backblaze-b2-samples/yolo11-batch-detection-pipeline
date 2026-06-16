<!-- last_verified: 2026-06-16 -->
# Completed: Initial Scaffold — YOLO11 Batch Detection Pipeline

Scaffolded from the `vibe-coding-starter-kit`. This plan records the delta that
turned the starter into the YOLO11 batch-detection pipeline.

## Outcome

A batch computer-vision pipeline: point a run at a B2 source prefix; the backend
reads media over the S3-compatible API, runs Ultralytics YOLO11 (detect/segment)
locally and keyless, and writes COCO JSON, annotated frames, and class-organized
instance crops back to B2 under a per-run prefix. B2 credentials are the only
secret.

## Kept from the starter

- UI kit / design system (`components/ui/`, `globals.css`, `/design`)
- Full-bucket File Explorer (`/files`) and Upload (`/upload`, retargeted to `…/source/`)
- Layered FastAPI backend, structural tests, JSON logging, `/health`, `/metrics`
- pnpm workspace, dev tooling, Railway infra

## Added

- Backend `repo/`: `detection.py` (lazy Ultralytics YOLO11), `media.py`
  (cv2/Pillow decode + cropping), `annotate.py`, `run_store.py` (scoped B2 IO)
- Backend `service/`: `pipeline.py` (async orchestrator), `coco.py` (pure COCO),
  `runs.py`, `stats.py`
- Backend `runtime/runs.py` (`POST/GET/DELETE /runs`, `/detections`, `/export`, `/stats`)
- Backend `types/run.py` (`Run`, `Detection`, `ImageResult`, `RunStats`, …)
- Frontend: Runs Library (`/runs`), run detail with confidence slider
  (`/runs/[id]`), detection galleries, New Run dialog; pipeline dashboard
  (stats cards, B2 footprint card, recent-runs table)

## Trimmed

- Starter dashboard defaults (stats-cards, upload-chart, recent-uploads-table)
- Metadata-extraction as a headline feature (light image metadata kept in `/files`)
- `PyPDF2` dependency and PDF handling
- Upload e2e spec rewritten to a navigation smoke test

## Standards (parent CLAUDE.md)

1. S3-compatible API only — no b2-native API
2. Custom user agent `b2ai-yolo11-batch-detection-pipeline` on the single boto3 client
3. Standard `B2_*` env names incl. `B2_REGION` + `B2_APPLICATION_KEY_ID`
   (the starter predated Standard #3 — fixed here)

All external SDKs (`ultralytics`, `cv2`, `numpy`, `PIL`) confined to `app/repo/`;
verified by `tests/test_structure.py`.
