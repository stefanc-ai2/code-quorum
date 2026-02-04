from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import session_registry
from claude_session_resolver import resolve_claude_session
from project_id import compute_cq_project_id


class _FakeBackend:
    def __init__(self, alive: set[str]):
        self._alive = set(alive)

    def is_alive(self, pane_id: str) -> bool:
        return pane_id in self._alive


def _write_registry_file(home: Path, session_id: str, payload: dict) -> Path:
    path = home / ".cq" / "run" / f"{session_registry.REGISTRY_PREFIX}{session_id}{session_registry.REGISTRY_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_resolve_claude_session_filters_by_session_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(
        session_registry,
        "get_backend_for_session",
        lambda _rec: _FakeBackend(alive={"%a", "%b"}),
    )

    work_dir = tmp_path / "repo"
    work_dir.mkdir()
    (work_dir / ".cq_config").mkdir()
    pid = compute_cq_project_id(work_dir)
    now = int(time.time())

    _write_registry_file(
        tmp_path,
        "a",
        {
            "cq_session_id": "a",
            "cq_session_name": "a",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "updated_at": now - 1,
            "providers": {"claude": {"pane_id": "%a"}},
        },
    )
    _write_registry_file(
        tmp_path,
        "b",
        {
            "cq_session_id": "b",
            "cq_session_name": "b",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "updated_at": now,
            "providers": {"claude": {"pane_id": "%b"}},
        },
    )

    explicit = resolve_claude_session(work_dir, session="a", env={})
    assert explicit is not None
    assert explicit.data.get("pane_id") == "%a"

    via_env = resolve_claude_session(work_dir, env={"CQ_SESSION": "a"})
    assert via_env is not None
    assert via_env.data.get("pane_id") == "%a"


def test_resolve_claude_session_defaults_to_default_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(
        session_registry,
        "get_backend_for_session",
        lambda _rec: _FakeBackend(alive={"%default", "%feature"}),
    )

    work_dir = tmp_path / "repo"
    work_dir.mkdir()
    (work_dir / ".cq_config").mkdir()
    pid = compute_cq_project_id(work_dir)
    now = int(time.time())

    # Legacy/default record: no cq_session_name -> treated as "default".
    _write_registry_file(
        tmp_path,
        "default",
        {
            "cq_session_id": "default",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "updated_at": now - 1,
            "providers": {"claude": {"pane_id": "%default"}},
        },
    )

    # Newer, but should not be selected unless CQ_SESSION/session is set.
    _write_registry_file(
        tmp_path,
        "feature-x",
        {
            "cq_session_id": "feature-x",
            "cq_session_name": "feature-x",
            "cq_project_id": pid,
            "work_dir": str(work_dir),
            "terminal": "tmux",
            "updated_at": now,
            "providers": {"claude": {"pane_id": "%feature"}},
        },
    )

    resolved = resolve_claude_session(work_dir, env={})
    assert resolved is not None
    assert resolved.data.get("pane_id") == "%default"
