<!-- last_verified: 2026-03-10 -->
# Feature: Annotations & Crops

## Purpose
Produce two derived image datasets per run — annotated frames (boxes/labels, and
masks in segment mode) and class-organized instance crops — and surface the
storage-footprint multiplier they create on B2.

## Used By
- UI: `/runs/[id]` annotated-frame gallery + per-class crop gallery; dashboard footprint card
- API: `GET /runs/{id}/detections` (presigned annotated/crop URLs)
- Job: written during the pipeline (ANNOTATING / CROPPING)

## Core Functions
- `services/api/app/repo/annotate.py` — `detect_and_annotate()` → (detections, annotated JPEG)
- `services/api/app/repo/detection.py` — `detect_and_render()` uses YOLO11 `Results.plot()`
- `services/api/app/repo/media.py` — `crop_instances()` crops each bbox to JPEG; `encode_jpeg()`
- `services/api/app/repo/run_store.py` — `annotated_key`, `crop_key`
- `apps/web/src/components/runs/detection-gallery.tsx` — annotated + crop galleries

## Canonical Files
- Annotation adapter: `services/api/app/repo/annotate.py`
- Cropping: `services/api/app/repo/media.py`

## Inputs
- Decoded BGR frame + the run's task/model (inside `repo/` only)

## Outputs
- Annotated frame: `runs/{id}/annotated/{stem}.jpg`
- Instance crops: `runs/{id}/crops/{class}/{stem}-{n}.jpg` (highest score first, capped by `max_crops_per_image`)
- `derived_bytes` accumulates on the manifest → drives the dashboard footprint multiplier

## Flow
- For each frame, `detect_and_annotate` runs inference once and returns the
  annotated JPEG (YOLO's own renderer) plus plain detections
- Crops are cut from the same frame for each detection (clamped to bounds; degenerate boxes skipped)
- Each crop is filed under its class folder; class folder names are sanitized
- The run detail view filters both galleries client-side by the confidence slider

## Edge Cases
- Detection box partly off-frame → clamped before cropping
- Degenerate (zero-area) box → crop skipped
- More than `max_crops_per_image` detections → top-N by score are cropped
- Segment task → masks drawn on the annotated frame; crops are still bbox crops

## UX States
- Frames tab: annotated images with a "N det" badge reflecting the threshold
- Crops tab: grouped by class with per-class counts; empty when threshold filters all out

## Verification
- Test files: `services/api/tests/test_structure.py` (SDK containment), `services/api/tests/test_runs.py`
- Required cases: SDK confined to `repo/`, run aggregates populate
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: tests green; `cv2`/`ultralytics`/`numpy` never imported outside `repo/`

## Related Docs
- [Batch Detection Runs](batch-detection.md)
- [Dashboard](dashboard.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
