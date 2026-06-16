<!-- last_verified: 2026-03-10 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with pipeline metrics + the B2 footprint multiplier
  - Runs Library (`/runs`) — scoped explorer over this app's prefix + New Run dialog
  - Run detail (`/runs/[id]`) — confidence slider, annotated-frame gallery, crop gallery, COCO export
  - Upload (source media) and full-bucket File Explorer (`/files`)
- **services/api/** — FastAPI backend (layered architecture)
  - Async batch-detection pipeline (FastAPI `BackgroundTasks`)
  - **Ultralytics YOLO11** detect/segment — confined to `app/repo/`
  - B2 S3 integration via boto3 — confined to `app/repo/`
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing + Prometheus metrics
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## The Pipeline

A run is started via `POST /runs`, which writes an initial `manifest.json` to B2
and kicks off a `BackgroundTask`. The task advances through these stages,
persisting status to the manifest after each so the UI can poll live progress:

```
QUEUED -> LISTING -> DETECTING -> ANNOTATING -> CROPPING -> READY
                                                            (or FAILED)
```

- **LISTING** — `list_objects_v2` enumerates image/video media under the run's
  source prefix (capped by `max_images_per_run`); records `source_bytes`.
- **DETECTING / ANNOTATING / CROPPING** — per image (or per sampled video frame):
  decode → run YOLO11 once → write the annotated frame, per-image COCO JSON, and
  class-organized crops to B2. Aggregates (`detection_count`, `crop_count`,
  `class_counts`, `derived_bytes`) update on the manifest as work proceeds.
- **READY** — the combined COCO `instances.json` dataset is assembled and written.

The orchestrator (`service/pipeline.py`) **never raises**: any failure is caught
and recorded as `status=FAILED` with an error message on the manifest.

### B2 key layout (the data store)

There is no database and no queue — each run's `manifest.json` is the single
source of truth. Everything is scoped under `settings.run_prefix`:

```
yolo11-batch-detection-pipeline/
  source/                          # /upload target + default run source prefix
  runs/{run_id}/
    manifest.json                  # status + image index + aggregates
    coco/{stem}.json               # per-image COCO detections
    coco/instances.json            # combined COCO dataset (export artifact)
    annotated/{stem}.jpg           # annotated frames
    crops/{class}/{stem}-{n}.jpg   # class-organized instance crops
```

## Backend Layering

```
types/     Pydantic models (Run, ImageResult, Detection, RunStats) — no logic
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access + external SDKs (boto3 B2, Ultralytics, cv2) — no business logic
  |
service/   Business logic (pipeline, coco, runs, stats) — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3`, `ultralytics`, `cv2`, `numpy`, `PIL` only allowed in `repo/`
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Repo adapters (where every external SDK lives)

- `repo/b2_client.py` — the single boto3 S3 client (custom user agent set here)
- `repo/run_store.py` — scoped B2 key builders, object IO, manifest read/write,
  scoped listing + scoped delete
- `repo/detection.py` — **the only place `ultralytics` is imported** (lazily);
  loads YOLO11 once via `lru_cache`, returns plain `Detection` models + an
  annotated frame
- `repo/media.py` — image/video decode, frame sampling, instance cropping, JPEG
  encoding (`cv2`/`numpy`, lazy)
- `repo/annotate.py` — composes detection + media into `(detections, annotated
  JPEG bytes)` so the service never sees a CV type

## Boundary Invariants

- **No external SDK leakage**: `boto3`/`ultralytics`/`cv2`/`numpy`/`PIL` are only
  imported in `app/repo/`. The service layer reasons over plain Pydantic models.
- **Lazy CV imports**: `ultralytics`/`cv2` are imported inside functions so the
  modules stay importable for structural tests without the CV runtime installed.
- **No raw dicts at boundaries**: typed Pydantic models cross every layer.
- **No mutable globals**: configuration is read-only after init.
- **Validated inputs**: HTTP inputs validated by FastAPI/Pydantic; run ids and
  source prefixes are validated (no traversal); file keys checked against allowlist.

## Deployment

- **Local dev** — `pnpm dev` runs both services (web on `:3000`, API on `:8000`).
- **Railway** — two services from the same repo; see `infra/railway/README.md`.
  Note the API image installs the CV runtime (torch) — size the build accordingly.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API). Source corpus, every
  derived artifact, and the per-run `manifest.json` index. No application database.

## External Services

- **Backblaze B2 S3 API** — read source media; write COCO/annotated/crops; presign previews.
- **Ultralytics YOLO11** — runs **locally** on pre-trained COCO weights, no API
  key; weights auto-download on first use. No external inference service.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for inline previews and the COCO export

## Data Flows

- **Start run**: Browser -> `POST /runs` -> service writes manifest -> BackgroundTask
- **Pipeline**: task reads source from B2 -> YOLO11 -> writes artifacts + manifest to B2
- **Poll**: Browser -> `GET /runs/{id}` (4s while active) -> manifest from B2
- **Browse**: Browser -> `GET /runs/{id}/detections` -> presigned annotated/crop URLs
- **Export**: Browser -> `GET /runs/{id}/export` -> presigned `instances.json` URL
- **Delete**: Browser -> `DELETE /runs/{id}` -> scoped delete of that run's prefix only

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware
- `/metrics` endpoint (Prometheus format)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Pipeline orchestrator: `services/api/app/service/pipeline.py`
- Pure COCO assembly: `services/api/app/service/coco.py`
- YOLO11 adapter: `services/api/app/repo/detection.py`
- B2 data access (run store): `services/api/app/repo/run_store.py`
- B2 S3 client: `services/api/app/repo/b2_client.py`
- Run routes: `services/api/app/runtime/runs.py`
- Pydantic models: `services/api/app/types/run.py`
- Config: `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Batch Detection Runs](docs/features/batch-detection.md)
- [COCO Output](docs/features/coco-output.md)
- [Annotations & Crops](docs/features/annotations-and-crops.md)
- [Runs Library](docs/features/runs-library.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
