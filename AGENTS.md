<!-- last_verified: 2026-05-01 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/                /, /upload, /runs, /runs/[id], /files, /settings,
                          /design
  src/components/runs/         Runs Library, run detail, new-run dialog,
                          detection gallery (annotated frames + crops),
                          status badge
  src/components/dashboard/    Pipeline stats cards, B2 footprint card,
                          recent-runs table
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/               b2_client, run_store (B2); detection (Ultralytics
                          YOLO11), media (cv2/Pillow decode + cropping),
                          annotate (YOLO render) — ALL external SDKs live here
  app/service/            pipeline (async orchestrator), coco (pure COCO
                          assembly), runs, stats, files, metadata, upload
  app/runtime/            runs, files, upload, health, metrics
packages/shared/   Shared TypeScript types (Run, Detection, RunStats, …)
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

The detection pipeline is async (FastAPI `BackgroundTasks`); status is persisted
in each run's `manifest.json` on B2 (the sole data store — no DB, no queue). See
[ARCHITECTURE.md](ARCHITECTURE.md) for the pipeline stages and B2 layout.

## 2. Building on This App

This app was scaffolded from the `vibe-coding-starter-kit`. The starter contract
below still holds — keep these pieces; the rest is this app's detection pipeline.

**Keep as-is (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit the generated `components/ui/` files directly. Restyling happens through tokens in `globals.css`.
- **File Explorer.** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/` — the full-bucket browser. The Files sidebar entry stays.
- **Upload.** `/upload` route, `apps/web/src/app/upload/`, and `apps/web/src/components/upload/` — here it uploads source images/videos into this app's `…/source/` prefix.
- The sidebar nav (Dashboard, Upload, Runs, Files, Settings, plus the Design System utility link).

**This app's surface**
- **Runs Library** (`/runs`) — scoped asset explorer over this app's `…/runs/` prefix (distinct from the full-bucket `/files`), plus a New Run dialog (source prefix, task detect/segment, confidence).
- **Run detail** (`/runs/[id]`) — confidence-threshold slider that re-filters the stored detections client-side, annotated-frame gallery, per-class crop gallery, COCO dataset export. Live status poll while processing.
- **Dashboard** (`/`) — pipeline metrics (runs, images processed, detections, distinct classes) + the source-vs-derived B2 footprint multiplier + a recent-runs table with live status. New aggregations flow `runtime -> service -> repo` and are exposed via TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare `useEffect + fetch`.

**Pipeline invariant**
- Every external CV/media dependency in the detection pipeline is wrapped in a
  `repo/` adapter (`detection`, `media`, `annotate`). The service layer reasons
  over plain Pydantic models (`Run`, `ImageResult`, `Detection`) and **never**
  imports `ultralytics`, `cv2`, or `numpy` directly. Keep it that way.
  `ultralytics` is imported **lazily** inside `repo/detection.py` so structural
  tests stay importable without the CV runtime installed. (One scoped
  exception: the inherited `/files` image-metadata reader uses Pillow in
  `service/metadata.py` — that feature is the only place an external imaging
  library is permitted in the service layer.)
- The primary feature (detect/segment → annotate → crop → COCO) must stay
  **real** — no mocked detections, no synthetic crops. YOLO11 runs locally on
  pre-trained COCO weights with **no API key**; weights auto-download on first
  use. B2 credentials are the only secret.

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external APIs/SDKs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
