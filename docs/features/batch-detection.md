<!-- last_verified: 2026-03-10 -->
# Feature: Batch Detection Runs

## Purpose
Point a run at a B2 source prefix and run Ultralytics YOLO11 (detect or segment)
locally over the whole batch, writing derived artifacts back to B2 — the
app's primary feature.

## Used By
- UI: `/runs` (New Run dialog), `/runs/[id]` (live status)
- API: `POST /runs`, `GET /runs/{id}`
- Job: `service/pipeline.run_pipeline` (FastAPI `BackgroundTask`)

## Core Functions
- `services/api/app/service/pipeline.py` — async orchestrator (LISTING → DETECTING → ANNOTATING → CROPPING → READY)
- `services/api/app/repo/detection.py` — **only place `ultralytics` is imported** (lazy); loads YOLO11 once via `lru_cache`
- `services/api/app/repo/media.py` — image/video decode, frame sampling, cropping (cv2/numpy, lazy)
- `services/api/app/repo/annotate.py` — composes detection + media into annotated JPEG bytes
- `services/api/app/repo/run_store.py` — scoped B2 IO + manifest read/write
- `services/api/app/service/runs.py` — run register/get/list/delete

## Canonical Files
- Pipeline orchestrator: `services/api/app/service/pipeline.py`
- YOLO11 adapter: `services/api/app/repo/detection.py`

## Inputs
- name: string (run label)
- source_prefix: string (B2 prefix; blank → `…/source/`; no `..` traversal)
- task: `"detect" | "segment"`
- model: string (optional; defaults to `yolo11n.pt` / `yolo11n-seg.pt`)
- min_confidence: float 0–1 (server-side detection floor)

## Outputs
- `Run` (status=queued) returned immediately; pipeline runs async
- Side effects on B2: per-image COCO JSON, combined `instances.json`, annotated
  frames, class-organized crops, and the run `manifest.json`

## Flow
- `POST /runs` validates input, writes the initial manifest, kicks off a BackgroundTask
- LISTING: `list_objects_v2` enumerates image/video media under the prefix (capped by `max_images_per_run`)
- For each image (or sampled video frame at `video_frame_stride`): decode → YOLO11 → write annotated frame + per-image COCO + crops
- Aggregates (detection_count, crop_count, class_counts, derived_bytes) update on the manifest as work proceeds
- CROPPING/READY: assemble + write the combined COCO dataset, mark READY

## Edge Cases
- No media under the prefix → run marked FAILED with an explanatory error
- Source object vanishes mid-run → skipped with a warning, run continues
- Any unexpected error → caught; run marked FAILED (the worker never crashes)
- Unknown task / traversal prefix → `POST /runs` returns 400
- Confidence outside 0–1 → clamped

## UX States
- Active (queued…cropping): live "Detection in progress…" panel, page auto-polls
- Failed: destructive alert with the error message
- Ready: confidence slider + annotated/crop galleries + COCO export

## Verification
- Test files: `services/api/tests/test_runs.py`, `services/api/tests/test_coco.py`, `services/api/tests/test_structure.py`
- Required cases: run creation defaults/validation, COCO assembly, SDK containment
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green; `ultralytics`/`cv2` never imported outside `repo/`

## Related Docs
- [COCO Output](coco-output.md)
- [Annotations & Crops](annotations-and-crops.md)
- [Runs Library](runs-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
