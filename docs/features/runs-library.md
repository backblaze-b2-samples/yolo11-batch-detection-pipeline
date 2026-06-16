<!-- last_verified: 2026-03-10 -->
# Feature: Runs Library & Confidence Browsing

## Purpose
A scoped explorer over this app's `…/runs/` prefix (distinct from the full-bucket
`/files`) where you start runs, watch live status, browse results by a
confidence-threshold slider, preview annotated frames and crops via presigned
URLs, and export the COCO dataset.

## Used By
- UI: `/runs` (library + New Run dialog), `/runs/[id]` (detail)
- API: `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/detections`, `GET /runs/{id}/export`, `DELETE /runs/{id}`

## Core Functions
- `apps/web/src/components/runs/runs-library.tsx` — run cards with status + counts
- `apps/web/src/components/runs/new-run-dialog.tsx` — start a run (prefix, task, confidence)
- `apps/web/src/components/runs/run-detail.tsx` — confidence slider + galleries + export/delete
- `apps/web/src/components/runs/detection-gallery.tsx` — annotated + per-class crop galleries
- `apps/web/src/lib/queries.ts` — `useRuns`, `useRun`, `useRunDetections`, `useCreateRun`, `useDeleteRun`
- `services/api/app/service/runs.py` — list/get/detections_view/export/delete

## Canonical Files
- Run detail (confidence slider): `apps/web/src/components/runs/run-detail.tsx`
- Detections view: `services/api/app/service/runs.py` (`detections_view`)

## Inputs
- New run: name, source_prefix, task, min_confidence (from the dialog)
- Detail: run id (route param); confidence threshold (client-side slider state)

## Outputs
- `GET /runs` → `RunSummary[]` (newest first; thumbnail = first annotated frame)
- `GET /runs/{id}/detections` → per-image detections + presigned annotated/crop URLs
- `GET /runs/{id}/export` → `{ url }` presigned COCO download
- `DELETE /runs/{id}` → scoped delete (objects_removed count)

## Flow
- Library lists runs scoped to this app's prefix; cards show status, image/detection/crop counts
- New Run dialog posts `POST /runs` and routes to the detail page
- Detail polls `GET /runs/{id}` every 4s while active; once READY it loads `/detections`
- The confidence slider (floored at the run's `min_confidence`) re-filters the
  **stored** detections client-side — no model re-run — updating both galleries and counts
- Export opens the presigned `instances.json`; Delete scopes to this run's prefix only

## Edge Cases
- Run still processing → galleries hidden, live progress panel shown
- Run produced no detections → "No detections" empty state
- Threshold filters everything out → "No crops at this confidence threshold"
- Delete → removes only `…/runs/{id}/`, never the source corpus or other runs

## UX States
- Library: loading skeletons / error+retry / empty / populated cards
- Detail: active (polling) / failed (alert) / ready (slider + tabs)

## Verification
- Test files: `services/api/tests/test_runs.py`
- Required cases: create-run defaults/validation, segment model selection, traversal rejection, confidence clamp
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: run-service tests green; eslint/tsc clean on the runs UI

## Related Docs
- [Batch Detection Runs](batch-detection.md)
- [COCO Output](coco-output.md)
- [Annotations & Crops](annotations-and-crops.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
