"""HTTP surface for batch detection runs. No business logic here — handlers
validate input, delegate to the service layer, and map domain errors to HTTP."""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.service import runs as runs_service
from app.service import stats as stats_service
from app.service.pipeline import run_pipeline
from app.service.runs import RunError, RunNotFound
from app.types import Run, RunStats, RunSummary

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateRunRequest(BaseModel):
    name: str = ""
    source_prefix: str = ""
    task: str = "detect"
    model: str | None = None
    min_confidence: float = Field(default=0.25, ge=0.0, le=1.0)


@router.get("/runs/stats", response_model=RunStats)
async def run_stats_endpoint():
    return stats_service.get_run_stats()


@router.post("/runs", response_model=Run, status_code=201)
async def create_run_endpoint(body: CreateRunRequest, background: BackgroundTasks):
    try:
        run = runs_service.create_run(
            name=body.name,
            source_prefix=body.source_prefix,
            task=body.task,
            model=body.model,
            min_confidence=body.min_confidence,
        )
    except RunError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    # Kick off the CV pipeline asynchronously; status is polled via GET.
    background.add_task(run_pipeline, run.id)
    return run


@router.get("/runs", response_model=list[RunSummary])
async def list_runs_endpoint():
    return runs_service.list_runs()


@router.get("/runs/{run_id}", response_model=Run)
async def get_run_endpoint(run_id: str):
    try:
        return runs_service.get_run(run_id)
    except RunError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RunNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/runs/{run_id}/detections")
async def run_detections_endpoint(run_id: str):
    try:
        return runs_service.detections_view(run_id)
    except RunError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RunNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/runs/{run_id}/export")
async def run_export_endpoint(run_id: str):
    try:
        return {"url": runs_service.export_url(run_id)}
    except RunError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RunNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.delete("/runs/{run_id}")
async def delete_run_endpoint(run_id: str):
    try:
        count = runs_service.delete_run(run_id)
    except RunError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RunNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"deleted": True, "id": run_id, "objects_removed": count}
