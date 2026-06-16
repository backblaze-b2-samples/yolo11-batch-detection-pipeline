<!-- last_verified: 2026-03-10 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the batch-detection pipeline: how many runs and
detections have happened, how many distinct classes were seen, and the
source-vs-derived B2 storage footprint multiplier (the strategic B2 story).

## Used By
- UI: `/` page (dashboard home)
- API: `GET /runs/stats`

## Core Functions
- `apps/web/src/components/dashboard/pipeline-stats-cards.tsx` — 4 stat cards (runs, images processed, detections, distinct classes)
- `apps/web/src/components/dashboard/footprint-card.tsx` — source-vs-derived footprint multiplier + crops count
- `apps/web/src/components/dashboard/recent-runs-table.tsx` — recent runs with live status
- `apps/web/src/lib/queries.ts` — `useRunStats()` (polls while any run is active)
- `services/api/app/runtime/runs.py` — `GET /runs/stats` handler
- `services/api/app/service/stats.py` — `get_run_stats()` aggregation
- `services/api/app/repo/run_store.py` — scoped run listing + manifest reads

## Canonical Files
- Stats service logic: `services/api/app/service/stats.py`
- Footprint card: `apps/web/src/components/dashboard/footprint-card.tsx`

## Inputs
- None (dashboard loads data automatically; polls every 4s while a run is active)

## Outputs
- `GET /runs/stats` → `RunStats`: runs, images_processed, detections,
  crops_generated, distinct_classes, source_bytes(+human), derived_bytes(+human),
  footprint_multiplier, recent (up to 8 `RunSummary`)

## Flow
- Page loads → `useRunStats()` fetches aggregates by scanning this app's run manifests
- Stat cards display run/image/detection/class totals
- Footprint card shows `derived_bytes / source_bytes` as a ×multiplier with a
  source-vs-derived bar and total crops generated
- Recent-runs table lists the latest runs with a live status badge
- While any run is active, the dashboard polls every 4s and stops once terminal

## Edge Cases
- API unavailable → inline `ErrorState` with retry (does not render fake zeros)
- No runs yet → cards show 0, footprint multiplier shows 0×, table empty state
- Zero source bytes (run still listing) → multiplier defensively shows 0×

## UX States
- Loading: skeleton placeholders for cards and footprint card
- Empty: zeros + "No runs yet" table empty state
- Loaded: populated cards, footprint multiplier, recent-runs table

## Verification
- Test files: `services/api/tests/test_runs.py` (run aggregation feeds these cards)
- Required cases: stats with runs, empty bucket, API error fallback
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Batch Detection Runs](batch-detection.md)
- [App Workflows](../app-workflows.md)
