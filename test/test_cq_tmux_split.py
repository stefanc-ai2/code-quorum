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
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
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
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMUX_PANE", "%0")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

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

    session_file = tmp_path / ".cq_config" / ".codex-session"
    data = cq.json.loads(session_file.read_text(encoding="utf-8"))
    assert data["pane_id"] == pane_id
    assert "input_fifo" not in data
    assert "output_fifo" not in data
    assert "tmux_log" not in data


def test_start_codex_tmux_writes_session_file_session_scoped(monkeypatch, tmp_path: Path) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMUX_PANE", "%0")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

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

    launcher = cq.AILauncher(providers=["codex"], session_name="feature-x")
    launcher.terminal_type = "tmux"

    pane_id = launcher._start_codex_tmux()
    assert pane_id is not None

    session_file = tmp_path / ".cq_config" / "sessions" / "feature-x" / ".codex-session"
    data = cq.json.loads(session_file.read_text(encoding="utf-8"))
    assert data["pane_id"] == pane_id


def test_pane_title_markers_are_namespaced_by_session_and_run_id(monkeypatch, tmp_path: Path) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMUX_PANE", "%0")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

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

    launcher = cq.AILauncher(providers=["codex"], session_name="feature-x")
    launcher.terminal_type = "tmux"
    launcher.session_id = "ai-1234567890-99999"

    pane_id = launcher._start_codex_tmux()
    assert pane_id is not None

    session_file = tmp_path / ".cq_config" / "sessions" / "feature-x" / ".codex-session"
    data = cq.json.loads(session_file.read_text(encoding="utf-8"))
    assert data["pane_title_marker"] == "CQ-feature-x-Codex-567890-99999"


def test_pane_title_markers_are_unique_per_session(tmp_path: Path, monkeypatch) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)

    a = cq.AILauncher(providers=["codex"], session_name="a")
    a.session_id = "ai-1234567890-99999"
    b = cq.AILauncher(providers=["codex"], session_name="b")
    b.session_id = "ai-1234567890-99999"

    assert a._pane_title_marker("codex") == "CQ-a-Codex-567890-99999"
    assert b._pane_title_marker("codex") == "CQ-b-Codex-567890-99999"


def test_sessions_do_not_overwrite_session_files(monkeypatch, tmp_path: Path) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    launcher_a = cq.AILauncher(providers=["codex"], session_name="a")
    launcher_a.terminal_type = "tmux"
    launcher_a.session_id = "s-a"
    runtime_a = tmp_path / "runtime-a"
    runtime_a.mkdir(parents=True, exist_ok=True)
    assert launcher_a._write_codex_session(runtime_a, None, pane_id="%a", pane_title_marker="CQ-Codex") is True

    launcher_b = cq.AILauncher(providers=["codex"], session_name="b")
    launcher_b.terminal_type = "tmux"
    launcher_b.session_id = "s-b"
    runtime_b = tmp_path / "runtime-b"
    runtime_b.mkdir(parents=True, exist_ok=True)
    assert launcher_b._write_codex_session(runtime_b, None, pane_id="%b", pane_title_marker="CQ-Codex") is True

    a_path = tmp_path / ".cq_config" / "sessions" / "a" / ".codex-session"
    b_path = tmp_path / ".cq_config" / "sessions" / "b" / ".codex-session"
    assert a_path.exists()
    assert b_path.exists()

    data_a = cq.json.loads(a_path.read_text(encoding="utf-8"))
    data_b = cq.json.loads(b_path.read_text(encoding="utf-8"))
    assert data_a.get("pane_id") == "%a"
    assert data_b.get("pane_id") == "%b"


def test_cmd_start_namespaces_lock_by_session(monkeypatch, tmp_path: Path) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    monkeypatch.setattr(cq.tempfile, "gettempdir", lambda: str(tmp_path))
    # Ensure cmd_start's direct os.environ writes are cleaned up by monkeypatch undo.
    monkeypatch.setenv("CQ_SESSION", "")

    captured: dict[str, str] = {}

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            captured["provider"] = provider
            captured["cwd"] = str(cwd or "")
            self.lock_file = tmp_path / "cq.lock"

        def try_acquire(self) -> bool:
            return True

        def release(self) -> None:
            return None

    class _FakeLauncher:
        def __init__(self, *args, **kwargs):
            captured["session_name"] = str(kwargs.get("session_name") or "")

        def run_up(self) -> int:
            return 0

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)
    monkeypatch.setattr(cq, "AILauncher", _FakeLauncher)
    monkeypatch.setattr(cq, "load_start_config", lambda *_a, **_k: SimpleNamespace(data={}, path=None))

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["codex"],
            resume=False,
            auto=False,
            session="Feature-X",
        )
    )
    assert rc == 0
    assert captured["provider"] == "cq"
    assert captured["session_name"] == "feature-x"
    assert captured["cwd"].endswith(f"::{captured['session_name']}")


def test_cmd_start_lock_error_suggests_session_command(monkeypatch, tmp_path: Path, capsys) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.setenv("CQ_AUTO_SESSION", "0")

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            self.lock_file = tmp_path / "cq.lock"
            self.lock_file.write_text("46767\n", encoding="utf-8")

        def try_acquire(self) -> bool:
            return False

        def release(self) -> None:
            return None

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["claude", "codex"],
            resume=False,
            auto=False,
            session=None,
        )
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "❌ Another cq instance is already running for this directory/session (pid 46767)." in err
    assert "💡 Session: default" in err
    assert "cq --session default-2 claude codex" in err


def test_cmd_start_auto_selects_new_session_when_default_locked(monkeypatch, tmp_path: Path, capsys) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    # Ensure cmd_start's direct os.environ writes are cleaned up by monkeypatch undo.
    monkeypatch.setenv("CQ_SESSION", "")
    monkeypatch.delenv("CQ_AUTO_SESSION", raising=False)

    captured: dict[str, str] = {}

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            self.cwd = str(cwd or "")
            self.lock_file = tmp_path / "cq.lock"

        def try_acquire(self) -> bool:
            if self.cwd.endswith("::default"):
                self.lock_file.write_text("46767\n", encoding="utf-8")
                return False
            if self.cwd.endswith("::default-2"):
                return True
            return False

        def release(self) -> None:
            return None

    class _FakeLauncher:
        def __init__(self, *args, **kwargs):
            captured["session_name"] = str(kwargs.get("session_name") or "")

        def run_up(self) -> int:
            return 0

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)
    monkeypatch.setattr(cq, "AILauncher", _FakeLauncher)
    monkeypatch.setattr(cq, "load_start_config", lambda *_a, **_k: SimpleNamespace(data={}, path=None))

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["claude", "codex"],
            resume=False,
            auto=False,
            session=None,
        )
    )
    assert rc == 0
    assert captured["session_name"] == "default-2"
    err = capsys.readouterr().err
    assert "Auto-starting new session \"default-2\"" in err
    assert os.environ.get("CQ_SESSION") == "default-2"


def test_cmd_start_auto_selects_default_3_when_default_and_default_2_locked(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    # Ensure cmd_start's direct os.environ writes are cleaned up by monkeypatch undo.
    monkeypatch.setenv("CQ_SESSION", "")
    monkeypatch.delenv("CQ_AUTO_SESSION", raising=False)

    captured: dict[str, str] = {}

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            self.cwd = str(cwd or "")
            self.lock_file = tmp_path / "cq.lock"

        def try_acquire(self) -> bool:
            if self.cwd.endswith("::default"):
                self.lock_file.write_text("46767\n", encoding="utf-8")
                return False
            if self.cwd.endswith("::default-2"):
                return False
            if self.cwd.endswith("::default-3"):
                return True
            return False

        def release(self) -> None:
            return None

    class _FakeLauncher:
        def __init__(self, *args, **kwargs):
            captured["session_name"] = str(kwargs.get("session_name") or "")

        def run_up(self) -> int:
            return 0

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)
    monkeypatch.setattr(cq, "AILauncher", _FakeLauncher)
    monkeypatch.setattr(cq, "load_start_config", lambda *_a, **_k: SimpleNamespace(data={}, path=None))

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["claude", "codex"],
            resume=False,
            auto=False,
            session=None,
        )
    )
    assert rc == 0
    assert captured["session_name"] == "default-3"
    err = capsys.readouterr().err
    assert "Auto-starting new session \"default-3\"" in err
    assert os.environ.get("CQ_SESSION") == "default-3"


def test_cmd_start_explicit_session_lock_errors_without_auto_session(monkeypatch, tmp_path: Path, capsys) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    # Ensure any CQ_SESSION mutations don't leak.
    monkeypatch.setenv("CQ_SESSION", "")
    monkeypatch.delenv("CQ_AUTO_SESSION", raising=False)

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            self.lock_file = tmp_path / "cq.lock"
            self.lock_file.write_text("46767\n", encoding="utf-8")

        def try_acquire(self) -> bool:
            return False

        def release(self) -> None:
            return None

    class _FailLauncher:
        def __init__(self, *args, **kwargs):
            raise AssertionError("AILauncher should not be created when lock acquisition fails")

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)
    monkeypatch.setattr(cq, "AILauncher", _FailLauncher)

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["claude", "codex"],
            resume=False,
            auto=False,
            session="feature-x",
        )
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "💡 Session: feature-x" in err
    assert "Auto-starting new session" not in err
    assert "cq --session feature-x-2 claude codex" in err


def test_cmd_start_env_session_lock_errors_without_auto_session(monkeypatch, tmp_path: Path, capsys) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    monkeypatch.setenv("CQ_SESSION", "default")
    monkeypatch.delenv("CQ_AUTO_SESSION", raising=False)

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            self.lock_file = tmp_path / "cq.lock"
            self.lock_file.write_text("46767\n", encoding="utf-8")

        def try_acquire(self) -> bool:
            return False

        def release(self) -> None:
            return None

    class _FailLauncher:
        def __init__(self, *args, **kwargs):
            raise AssertionError("AILauncher should not be created when lock acquisition fails")

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)
    monkeypatch.setattr(cq, "AILauncher", _FailLauncher)

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["claude", "codex"],
            resume=False,
            auto=False,
            session=None,
        )
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "💡 Session: default" in err
    assert "Auto-starting new session" not in err
    assert "cq --session default-2 claude codex" in err


def test_cmd_start_no_auto_session_flag_disables_auto_session(monkeypatch, tmp_path: Path, capsys) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.delenv("CQ_AUTO_SESSION", raising=False)

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            self.lock_file = tmp_path / "cq.lock"
            self.lock_file.write_text("46767\n", encoding="utf-8")

        def try_acquire(self) -> bool:
            return False

        def release(self) -> None:
            return None

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["claude", "codex"],
            resume=False,
            auto=False,
            session=None,
            no_auto_session=True,
        )
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "💡 Session: default" in err
    assert "cq --session default-2 --no-auto-session claude codex" in err


def test_cmd_start_auto_session_exhaustion_errors(monkeypatch, tmp_path: Path, capsys) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cq, "detect_terminal", lambda: "tmux")
    monkeypatch.delenv("CQ_SESSION", raising=False)
    monkeypatch.delenv("CQ_AUTO_SESSION", raising=False)

    class _FakeLock:
        def __init__(self, provider: str, timeout: float = 60.0, cwd: str | None = None):
            self.cwd = str(cwd or "")
            self.lock_file = tmp_path / "cq.lock"

        def try_acquire(self) -> bool:
            if self.cwd.endswith("::default"):
                self.lock_file.write_text("46767\n", encoding="utf-8")
            return False

        def release(self) -> None:
            return None

    class _FailLauncher:
        def __init__(self, *args, **kwargs):
            raise AssertionError("AILauncher should not be created when auto-session exhausts")

    monkeypatch.setattr(cq, "ProviderLock", _FakeLock)
    monkeypatch.setattr(cq, "AILauncher", _FailLauncher)
    monkeypatch.setattr(cq, "load_start_config", lambda *_a, **_k: SimpleNamespace(data={}, path=None))

    rc = cq.cmd_start(
        SimpleNamespace(
            providers=["claude", "codex"],
            resume=False,
            auto=False,
            session=None,
        )
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "❌ All auto-session slots are in use" in err


def test_managed_env_includes_cq_session(monkeypatch, tmp_path: Path) -> None:
    cq = _load_cq_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)

    launcher = cq.AILauncher(providers=["codex"], session_name="feature-x")
    env = launcher._managed_env_overrides()
    assert env.get("CQ_SESSION") == "feature-x"
