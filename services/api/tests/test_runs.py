"""Run service tests (manifest store mocked — no real B2)."""

import pytest

from app.service import runs as runs_service
from app.service.runs import RunError


def test_create_run_defaults_blank_prefix_to_source(monkeypatch):
    saved = {}
    monkeypatch.setattr(runs_service.store, "write_manifest", lambda run: saved.update(run=run))
    run = runs_service.create_run(
        name="", source_prefix="", task="detect", model=None, min_confidence=0.25
    )
    assert run.source_prefix == "yolo11-batch-detection-pipeline/source/"
    assert run.name.startswith("run-")
    assert run.model == "yolo11n.pt"
    assert run.status.value == "queued"
    assert saved["run"].id == run.id


def test_create_run_segment_uses_seg_model(monkeypatch):
    monkeypatch.setattr(runs_service.store, "write_manifest", lambda run: None)
    run = runs_service.create_run(
        name="seg", source_prefix="some/prefix/", task="segment", model=None,
        min_confidence=0.5,
    )
    assert run.task.value == "segment"
    assert run.model == "yolo11n-seg.pt"


def test_create_run_rejects_traversal(monkeypatch):
    monkeypatch.setattr(runs_service.store, "write_manifest", lambda run: None)
    with pytest.raises(RunError):
        runs_service.create_run(
            name="x", source_prefix="../escape/", task="detect", model=None,
            min_confidence=0.25,
        )


def test_create_run_rejects_unknown_task(monkeypatch):
    monkeypatch.setattr(runs_service.store, "write_manifest", lambda run: None)
    with pytest.raises(RunError):
        runs_service.create_run(
            name="x", source_prefix="", task="classify", model=None,
            min_confidence=0.25,
        )


def test_create_run_clamps_confidence(monkeypatch):
    monkeypatch.setattr(runs_service.store, "write_manifest", lambda run: None)
    run = runs_service.create_run(
        name="x", source_prefix="", task="detect", model=None, min_confidence=5.0
    )
    assert run.min_confidence == 1.0
