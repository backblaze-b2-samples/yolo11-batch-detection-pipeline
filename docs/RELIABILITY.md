<!-- last_verified: 2026-03-06 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Pipeline Reliability

- The detection pipeline runs as a FastAPI `BackgroundTask`; status is persisted
  to each run's `manifest.json` on B2 after every stage, so a client that
  reconnects always sees accurate progress
- The orchestrator (`service/pipeline.py`) **never raises**: any failure is
  caught and recorded as `status=FAILED` with a truncated error message — a
  failed run never crashes the worker or blocks other runs
- A run with no source media under its prefix is marked FAILED with a clear message
- A source object that disappears mid-run is skipped with a warning; the run continues
- YOLO11 weights auto-download on first use and are cached by the Ultralytics
  engine; the model is loaded once per process via `lru_cache`

## Graceful Degradation

- File / run listing returns an empty list (not an error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Per-image crop/annotation failures are isolated; the rest of the batch proceeds
- Frontend shows skeleton states while loading, error states on failure, and
  polls live status while a run is active

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
