from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load_cq_mounted_module(repo_root: Path):
    loader = SourceFileLoader("cq_mounted", str(repo_root / "bin" / "cq-mounted"))
    spec = importlib.util.spec_from_loader("cq_mounted", loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cq_mounted_filters_inactive_sessions_simple(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True)

    (work_dir / ".cq_config" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    (work_dir / ".cq_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--simple"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    assert out == "codex"


def test_cq_mounted_include_inactive(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True)

    (work_dir / ".cq_config" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    (work_dir / ".cq_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json", "--include-inactive"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex", "claude"]


def test_cq_mounted_missing_active_treated_as_active(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True)

    (work_dir / ".cq_config" / ".codex-session").write_text(json.dumps({"pane_id": "1"}), encoding="utf-8")
    (work_dir / ".cq_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex"]


def test_cq_mounted_malformed_json_treated_as_active(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True)

    (work_dir / ".cq_config" / ".codex-session").write_text("not valid json {{{", encoding="utf-8")
    (work_dir / ".cq_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex"]


def test_cq_mounted_active_null_treated_as_active(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True)

    (work_dir / ".cq_config" / ".codex-session").write_text(json.dumps({"active": None}), encoding="utf-8")
    (work_dir / ".cq_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex"]


def test_cq_mounted_uses_env_session_strict(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True)

    # Default session exists, but env selects a named session with no files.
    (work_dir / ".cq_config" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    monkeypatch.setenv("CQ_SESSION", "feature-x")

    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["session"] == "feature-x"
    assert payload["mounted"] == []


def test_cq_mounted_session_flag_selects_session(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config" / "sessions" / "feature-x").mkdir(parents=True)
    (work_dir / ".cq_config" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    (work_dir / ".cq_config" / "sessions" / "feature-x" / ".codex-session").write_text(
        json.dumps({"active": True}), encoding="utf-8"
    )

    monkeypatch.setenv("CQ_SESSION", "other")
    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json", "--session", "feature-x"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["session"] == "feature-x"
    assert payload["mounted"] == ["codex"]


def test_cq_mounted_all_sessions_lists_default_and_named(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config" / "sessions" / "a").mkdir(parents=True)
    (work_dir / ".cq_config" / "sessions" / "b").mkdir(parents=True)
    (work_dir / ".cq_config" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    (work_dir / ".cq_config" / "sessions" / "a" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    (work_dir / ".cq_config" / "sessions" / "b" / ".claude-session").write_text(json.dumps({"active": True}), encoding="utf-8")

    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setattr(cq_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(cq_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json", "--all-sessions"])
    cq_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    sessions = payload["sessions"]
    assert [s["session"] for s in sessions] == ["default", "a", "b"]
    assert sessions[0]["mounted"] == ["codex"]
    assert sessions[1]["mounted"] == ["codex"]
    assert sessions[2]["mounted"] == ["claude"]


def test_cq_mounted_rejects_invalid_session_flag(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cq_mounted = _load_cq_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True)

    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setattr(cq_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--session", "../oops"])
    rc = cq_mounted.main()
    assert rc == 2
    err = capsys.readouterr().err
    assert "Invalid --session" in err
