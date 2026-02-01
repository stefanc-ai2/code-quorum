from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load_ccb_mounted_module(repo_root: Path):
    loader = SourceFileLoader("cq_mounted", str(repo_root / "bin" / "cq-mounted"))
    spec = importlib.util.spec_from_loader("cq_mounted", loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ccb_mounted_filters_inactive_sessions_simple(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ccb_mounted = _load_ccb_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".ccb_config").mkdir(parents=True)

    (work_dir / ".ccb_config" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    (work_dir / ".ccb_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.setattr(ccb_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(ccb_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(ccb_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--simple"])
    ccb_mounted.main()

    out = capsys.readouterr().out.strip()
    assert out == "codex"


def test_ccb_mounted_include_inactive(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ccb_mounted = _load_ccb_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".ccb_config").mkdir(parents=True)

    (work_dir / ".ccb_config" / ".codex-session").write_text(json.dumps({"active": True}), encoding="utf-8")
    (work_dir / ".ccb_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.setattr(ccb_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(ccb_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(ccb_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json", "--include-inactive"])
    ccb_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex", "claude"]


def test_ccb_mounted_missing_active_treated_as_active(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ccb_mounted = _load_ccb_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".ccb_config").mkdir(parents=True)

    (work_dir / ".ccb_config" / ".codex-session").write_text(json.dumps({"pane_id": "1"}), encoding="utf-8")
    (work_dir / ".ccb_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.setattr(ccb_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(ccb_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(ccb_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json"])
    ccb_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex"]


def test_ccb_mounted_malformed_json_treated_as_active(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ccb_mounted = _load_ccb_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".ccb_config").mkdir(parents=True)

    (work_dir / ".ccb_config" / ".codex-session").write_text("not valid json {{{", encoding="utf-8")
    (work_dir / ".ccb_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.setattr(ccb_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(ccb_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(ccb_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json"])
    ccb_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex"]


def test_ccb_mounted_active_null_treated_as_active(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ccb_mounted = _load_ccb_mounted_module(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".ccb_config").mkdir(parents=True)

    (work_dir / ".ccb_config" / ".codex-session").write_text(json.dumps({"active": None}), encoding="utf-8")
    (work_dir / ".ccb_config" / ".claude-session").write_text(json.dumps({"active": False}), encoding="utf-8")

    monkeypatch.setattr(ccb_mounted, "can_connect_localhost", lambda: True)
    monkeypatch.setattr(ccb_mounted, "pane_alive_for_session", lambda _data: None)

    monkeypatch.setattr(ccb_mounted.sys, "argv", ["cq-mounted", str(work_dir), "--json"])
    ccb_mounted.main()

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["mounted"] == ["codex"]
