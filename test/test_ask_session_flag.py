from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


def _load_ask_module(repo_root: Path):
    loader = SourceFileLoader("ask_bin", str(repo_root / "bin" / "ask"))
    spec = importlib.util.spec_from_loader("ask_bin", loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ask_passes_session_flag_to_loader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ask = _load_ask_module(repo_root)

    monkeypatch.chdir(tmp_path)

    sent: dict[str, str] = {}

    class _Backend:
        def send_text(self, pane_id: str, text: str) -> None:
            sent["pane_id"] = pane_id
            sent["text"] = text

    class _Session:
        def ensure_pane(self):
            return True, "pane-1"

        def backend(self):
            return _Backend()

    def _fake_load_codex_session(work_dir: Path, *, session=None, env=None):
        assert work_dir.resolve() == tmp_path.resolve()
        assert session == "feature-x"
        assert env is not None
        return _Session()

    monkeypatch.setattr(ask, "load_codex_session", _fake_load_codex_session)

    rc = ask.main(["ask", "--session", "feature-x", "codex", "--req-id", "abc", "hello"])
    assert rc == ask.EXIT_OK
    assert capsys.readouterr().out.strip() == "abc"
    assert sent["pane_id"] == "pane-1"
    assert "abc" in sent["text"]


def test_ask_uses_cq_session_env_when_no_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ask = _load_ask_module(repo_root)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CQ_SESSION", "env-session")

    sent: dict[str, str] = {}

    class _Backend:
        def send_text(self, pane_id: str, text: str) -> None:
            sent["pane_id"] = pane_id
            sent["text"] = text

    class _Session:
        def ensure_pane(self):
            return True, "pane-1"

        def backend(self):
            return _Backend()

    def _fake_load_codex_session(work_dir: Path, *, session=None, env=None):
        assert work_dir.resolve() == tmp_path.resolve()
        assert session is None
        assert env is not None
        assert env.get("CQ_SESSION") == "env-session"
        return _Session()

    monkeypatch.setattr(ask, "load_codex_session", _fake_load_codex_session)

    rc = ask.main(["ask", "codex", "--req-id", "abc", "hello"])
    assert rc == ask.EXIT_OK
    assert capsys.readouterr().out.strip() == "abc"
    assert sent["pane_id"] == "pane-1"
    assert "abc" in sent["text"]


def test_ask_rejects_invalid_session_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ask = _load_ask_module(repo_root)

    monkeypatch.chdir(tmp_path)

    rc = ask.main(["ask", "--session", "../oops", "codex", "hello"])
    assert rc == ask.EXIT_ERROR
    err = capsys.readouterr().err
    assert "Invalid --session" in err
