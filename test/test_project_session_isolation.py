from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import session_registry
from codex_session import load_project_session as load_codex_session
from claude_session import load_project_session as load_claude_session
from project_id import compute_cq_project_id


class _AliveBackend:
    def is_alive(self, _pane_id: str) -> bool:
        return True


def _write_registry_record(*, home: Path, session_id: str, record: dict) -> None:
    run_dir = home / ".cq" / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{session_registry.REGISTRY_PREFIX}{session_id}{session_registry.REGISTRY_SUFFIX}"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_claude_session_isolated_from_env_cross_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.delenv("CQ_ALLOW_CROSS_PROJECT_SESSION", raising=False)

    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    (repo_a / ".cq_config").mkdir(parents=True, exist_ok=True)
    (repo_b / ".cq_config").mkdir(parents=True, exist_ok=True)

    pid_a = compute_cq_project_id(repo_a)
    pid_b = compute_cq_project_id(repo_b)

    # Avoid tmux/wezterm dependencies in registry scans.
    monkeypatch.setattr(session_registry, "get_backend_for_session", lambda _data: _AliveBackend())

    session_a = "sess_a"
    session_b = "sess_b"

    now = int(time.time())
    _write_registry_record(
        home=home,
        session_id=session_a,
        record={
            "cq_session_id": session_a,
            "cq_project_id": pid_a,
            "work_dir": str(repo_a),
            "terminal": "tmux",
            "providers": {"claude": {"pane_id": "%a"}},
            "updated_at": now,
        },
    )
    _write_registry_record(
        home=home,
        session_id=session_b,
        record={
            "cq_session_id": session_b,
            "cq_project_id": pid_b,
            "work_dir": str(repo_b),
            "terminal": "tmux",
            "providers": {"claude": {"pane_id": "%b"}},
            "updated_at": now,
        },
    )

    # Point env at repo_b, but resolve from repo_a.
    monkeypatch.setenv("CQ_SESSION_ID", session_b)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("GEMINI_SESSION_ID", raising=False)
    monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)

    session = load_claude_session(repo_a)
    assert session is not None
    assert Path(session.work_dir).resolve() == repo_a.resolve()
    assert session.data.get("cq_project_id") == pid_a


def test_claude_session_allow_cross_project_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setenv("CQ_ALLOW_CROSS_PROJECT_SESSION", "1")

    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    (repo_a / ".cq_config").mkdir(parents=True, exist_ok=True)
    (repo_b / ".cq_config").mkdir(parents=True, exist_ok=True)

    pid_a = compute_cq_project_id(repo_a)
    pid_b = compute_cq_project_id(repo_b)

    monkeypatch.setattr(session_registry, "get_backend_for_session", lambda _data: _AliveBackend())

    session_a = "sess_a"
    session_b = "sess_b"
    now = int(time.time())
    _write_registry_record(
        home=home,
        session_id=session_a,
        record={
            "cq_session_id": session_a,
            "cq_project_id": pid_a,
            "work_dir": str(repo_a),
            "terminal": "tmux",
            "providers": {"claude": {"pane_id": "%a"}},
            "updated_at": now,
        },
    )
    _write_registry_record(
        home=home,
        session_id=session_b,
        record={
            "cq_session_id": session_b,
            "cq_project_id": pid_b,
            "work_dir": str(repo_b),
            "terminal": "tmux",
            "providers": {"claude": {"pane_id": "%b"}},
            "updated_at": now,
        },
    )

    monkeypatch.setenv("CQ_SESSION_ID", session_b)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("GEMINI_SESSION_ID", raising=False)
    monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)

    session = load_claude_session(repo_a)
    assert session is not None
    assert Path(session.work_dir).resolve() == repo_b.resolve()
    assert session.data.get("cq_project_id") == pid_b


def test_codex_session_loaded_only_from_current_directory(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    cfg_a = repo_a / ".cq_config"
    cfg_b = repo_b / ".cq_config"
    cfg_a.mkdir(parents=True, exist_ok=True)
    cfg_b.mkdir(parents=True, exist_ok=True)

    (cfg_a / ".codex-session").write_text(
        json.dumps({"terminal": "tmux", "pane_id": "%a", "work_dir": str(repo_a)}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (cfg_b / ".codex-session").write_text(
        json.dumps({"terminal": "tmux", "pane_id": "%b", "work_dir": str(repo_b)}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    session_a = load_codex_session(repo_a)
    session_b = load_codex_session(repo_b)
    assert session_a is not None
    assert session_b is not None
    assert session_a.session_file.resolve() == (cfg_a / ".codex-session").resolve()
    assert session_b.session_file.resolve() == (cfg_b / ".codex-session").resolve()
