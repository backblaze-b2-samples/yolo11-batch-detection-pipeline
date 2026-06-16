<!-- last_verified: 2026-03-10 -->
# Feature: COCO Output

## Purpose
Emit standard COCO-format object-detection JSON for every run — one file per
image plus a combined `instances.json` dataset — so results drop straight into
labeling tools and training pipelines.

## Used By
- UI: `/runs/[id]` "Export COCO" button
- API: `GET /runs/{id}/export`
- Job: written during the pipeline (per-image + combined)

## Core Functions
- `services/api/app/service/coco.py` — **pure** COCO assembly (no SDK imports)
  - `per_image_coco(image)` — COCO doc for a single image's detections
  - `combined_coco(images)` — combined dataset with de-duplicated categories
- `services/api/app/service/runs.py` — `export_url()` presigns `instances.json`
- `services/api/app/repo/run_store.py` — `coco_key`, `instances_key`, `presign_download`

## Canonical Files
- COCO assembly: `services/api/app/service/coco.py`

## Inputs
- `ImageResult` / `Detection` plain models (bbox in COCO `[x, y, w, h]` pixels)

## Outputs
- Per image: `runs/{id}/coco/{stem}.json`
- Combined: `runs/{id}/coco/instances.json` (export artifact)
- `GET /runs/{id}/export` → `{ url }` presigned download (attachment disposition)
- Each COCO doc has `images[]`, `annotations[]` (bbox, area, score, category_name), `categories[]`

## Flow
- During the pipeline, each image's detections are serialized to a per-image COCO file
- After all images are processed, `combined_coco` assembles one dataset:
  image ids are 1-based and distinct; annotation ids increment globally;
  categories are de-duplicated across images
- Export presigns the combined `instances.json` for download

## Edge Cases
- Image with no detections → COCO doc with empty `annotations[]` and `categories[]`
- Same class across many images → a single category entry (de-duplicated by id)
- Export before READY → 404 ("COCO dataset not ready")

## UX States
- Export button disabled until `instances_key` is present (run READY)

## Verification
- Test files: `services/api/tests/test_coco.py`
- Required cases: per-image shape, combined de-duplication + id increments
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: COCO tests green; assembly imports no SDK

## Related Docs
- [Batch Detection Runs](batch-detection.md)
- [Runs Library](runs-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
