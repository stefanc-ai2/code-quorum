from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import pytest

import session_registry
from session_registry import load_registry_by_project_id, upsert_registry
from project_id import compute_cq_project_id


class _FakeBackend:
    def __init__(self, alive: set[str], marker_map: Optional[dict[str, str]] = None):
        self._alive = set(alive)
        self._marker_map = dict(marker_map or {})

    def is_alive(self, pane_id: str) -> bool:
        return pane_id in self._alive

    def find_pane_by_title_marker(self, marker: str) -> str | None:
        return self._marker_map.get(marker)


def _write_registry_file(home: Path, session_id: str, payload: dict) -> Path:
    path = home / ".cq" / "run" / f"{session_registry.REGISTRY_PREFIX}{session_id}{session_registry.REGISTRY_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_upsert_registry_merges_providers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(session_registry, "get_backend_for_session", lambda _rec: _FakeBackend(alive={"%1"}))

    work_dir = tmp_path / "proj"
    work_dir.mkdir()
    pid = compute_cq_project_id(work_dir)

    ok1 = upsert_registry(
        {
            "cq_session_id": "s1",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "providers": {"codex": {"pane_id": "%1", "session_file": str(work_dir / ".cq_config" / ".codex-session")}},
        }
    )
    assert ok1 is True

    ok2 = upsert_registry(
        {
            "cq_session_id": "s1",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "providers": {"claude": {"pane_id": "%1", "session_file": str(work_dir / ".cq_config" / ".claude-session")}},
        }
    )
    assert ok2 is True

    reg_path = tmp_path / ".cq" / "run" / f"{session_registry.REGISTRY_PREFIX}s1{session_registry.REGISTRY_SUFFIX}"
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    assert data["cq_project_id"] == pid
    assert "providers" in data
    assert "codex" in data["providers"]
    assert "claude" in data["providers"]


def test_load_registry_by_project_id_filters_dead_panes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    work_dir = tmp_path / "proj"
    work_dir.mkdir()
    pid = compute_cq_project_id(work_dir)

    # Newer but dead.
    _write_registry_file(
        tmp_path,
        "new",
        {
            "cq_session_id": "new",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "updated_at": int(time.time()),
            "providers": {"codex": {"pane_id": "%dead"}},
        },
    )
    # Older but alive.
    _write_registry_file(
        tmp_path,
        "old",
        {
            "cq_session_id": "old",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "updated_at": int(time.time()) - 10,
            "providers": {"codex": {"pane_id": "%alive"}},
        },
    )

    monkeypatch.setattr(session_registry, "get_backend_for_session", lambda _rec: _FakeBackend(alive={"%alive"}))
    rec = load_registry_by_project_id(pid, "codex")
    assert rec is not None
    assert rec.get("cq_session_id") == "old"


def test_load_registry_by_project_id_infers_missing_project_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(session_registry, "get_backend_for_session", lambda _rec: _FakeBackend(alive={"%1"}))

    work_dir = tmp_path / "proj"
    work_dir.mkdir()
    pid = compute_cq_project_id(work_dir)

    # Legacy record missing cq_project_id (should infer from work_dir).
    _write_registry_file(
        tmp_path,
        "legacy",
        {
            "cq_session_id": "legacy",
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "updated_at": int(time.time()),
            "providers": {"codex": {"pane_id": "%1"}},
        },
    )

    rec = load_registry_by_project_id(pid, "codex")
    assert rec is not None
    assert rec.get("cq_session_id") == "legacy"
