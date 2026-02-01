from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace


def _load_cq_module() -> object:
    repo_root = Path(__file__).resolve().parents[1]
    cq_path = repo_root / "cq"
    loader = SourceFileLoader("cq_script", str(cq_path))
    spec = importlib.util.spec_from_loader("cq_script", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_run_up_sorts_providers_in_tmux(monkeypatch, tmp_path: Path) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ccb_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMUX_PANE", "%0")
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")

    # Use dummy provider tokens to exercise the generic provider path (i.e. not "claude" or "cmd").
    launcher = cq.AILauncher(providers=["provider_a", "provider_b", "codex"])
    launcher.terminal_type = "tmux"

    called: list[str] = []

    def _start_provider(p: str, **_kwargs) -> str:
        called.append(p)
        return f"%{len(called)}"

    monkeypatch.setattr(launcher, "_start_provider", _start_provider)
    monkeypatch.setattr(launcher, "_warmup_provider", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(launcher, "_start_claude", lambda: 0)
    monkeypatch.setattr(launcher, "_start_provider_in_current_pane", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(launcher, "cleanup", lambda: None)

    rc = launcher.run_up()
    assert rc == 0
    assert called == ["provider_b", "provider_a"]


def test_start_codex_tmux_writes_session_file(monkeypatch, tmp_path: Path) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ccb_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMUX_PANE", "%0")

    # Ensure runtime dir lands under tmp_path.
    monkeypatch.setattr(cq.tempfile, "gettempdir", lambda: str(tmp_path))

    # Fake tmux backend methods (no real tmux dependency).
    class _FakeTmuxBackend:
        def __init__(self, *args, **kwargs):
            self._created = 0

        def create_pane(
            self,
            cmd: str,
            cwd: str,
            direction: str = "right",
            percent: int = 50,
            parent_pane: str | None = None,
        ) -> str:
            self._created += 1
            return f"%{10 + self._created}"

        def set_pane_title(self, pane_id: str, title: str) -> None:
            return None

        def set_pane_user_option(self, pane_id: str, name: str, value: str) -> None:
            return None

        def respawn_pane(
            self,
            pane_id: str,
            *,
            cmd: str,
            cwd: str | None = None,
            stderr_log_path: str | None = None,
            remain_on_exit: bool = True,
        ) -> None:
            return None

    monkeypatch.setattr(cq, "TmuxBackend", _FakeTmuxBackend)

    # Fake `tmux display-message ... #{pane_pid}`.
    def _fake_run(argv, *args, **kwargs):
        if argv[:3] == ["tmux", "display-message", "-p"] and "#{pane_pid}" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="12345\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(cq.subprocess, "run", _fake_run)

    launcher = cq.AILauncher(providers=["codex"])
    launcher.terminal_type = "tmux"

    pane_id = launcher._start_codex_tmux()
    assert pane_id is not None

    runtime = Path(launcher.runtime_dir) / "codex"
    assert (runtime / "bridge.pid").exists() is False
    assert (runtime / "codex.pid").exists()
    assert (runtime / "codex.pid").read_text(encoding="utf-8").strip() == "12345"

    session_file = tmp_path / ".ccb_config" / ".codex-session"
    data = cq.json.loads(session_file.read_text(encoding="utf-8"))
    assert data["pane_id"] == pane_id
    assert "input_fifo" not in data
    assert "output_fifo" not in data
    assert "tmux_log" not in data
