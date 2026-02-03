from __future__ import annotations

import terminal


def test_wezterm_send_enter_defaults_to_auto_tries_key_first(monkeypatch) -> None:
    """Default should try send-key first (real key event), then return on success."""
    monkeypatch.delenv("CQ_WEZTERM_ENTER_METHOD", raising=False)
    monkeypatch.setattr(terminal, "_get_wezterm_bin", lambda: "/usr/bin/wezterm")
    monkeypatch.setattr(terminal.time, "sleep", lambda _: None)

    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        cmd = args[0]
        calls.append(cmd)
        if "send-key" in cmd:
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(terminal, "_run", fake_run)

    backend = terminal.WeztermBackend()
    backend._send_enter("123")

    assert any("send-key" in cmd for cmd in calls)
    assert not any("send-text" in cmd for cmd in calls)


def test_wezterm_send_enter_text_mode_does_not_use_send_key(monkeypatch) -> None:
    """Legacy mode should only use send-text CR injection."""
    monkeypatch.setenv("CQ_WEZTERM_ENTER_METHOD", "text")
    monkeypatch.setattr(terminal, "_get_wezterm_bin", lambda: "/usr/bin/wezterm")
    monkeypatch.setattr(terminal.time, "sleep", lambda _: None)

    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        cmd = args[0]
        calls.append(cmd)
        if "send-text" in cmd:
            assert kwargs.get("input") == b"\r"
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(terminal, "_run", fake_run)

    backend = terminal.WeztermBackend()
    backend._send_enter("123")

    assert any("send-text" in cmd for cmd in calls)
    assert not any("send-key" in cmd for cmd in calls)


def test_wezterm_send_enter_auto_falls_back_to_cr(monkeypatch) -> None:
    """Auto should fall back to CR when send-key isn't supported."""
    monkeypatch.delenv("CQ_WEZTERM_ENTER_METHOD", raising=False)
    monkeypatch.setattr(terminal, "_get_wezterm_bin", lambda: "/usr/bin/wezterm")
    monkeypatch.setattr(terminal.time, "sleep", lambda _: None)

    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        cmd = args[0]
        calls.append(cmd)
        if "send-key" in cmd:
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="nope")
        if "send-text" in cmd:
            assert kwargs.get("input") == b"\r"
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(terminal, "_run", fake_run)

    backend = terminal.WeztermBackend()
    backend._send_enter("123")

    assert any("send-key" in cmd for cmd in calls)
    assert any("send-text" in cmd for cmd in calls)


def test_wezterm_send_enter_key_mode_is_strict(monkeypatch) -> None:
    """Key mode should not fall back to CR injection if send-key fails."""
    monkeypatch.setenv("CQ_WEZTERM_ENTER_METHOD", "key")
    monkeypatch.setattr(terminal, "_get_wezterm_bin", lambda: "/usr/bin/wezterm")
    monkeypatch.setattr(terminal.time, "sleep", lambda _: None)

    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        cmd = args[0]
        calls.append(cmd)
        if "send-key" in cmd:
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="nope")
        if "send-text" in cmd:
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(terminal, "_run", fake_run)

    backend = terminal.WeztermBackend()
    backend._send_enter("123")

    assert any("send-key" in cmd for cmd in calls)
    assert not any("send-text" in cmd for cmd in calls)
    send_key_calls = [cmd for cmd in calls if "send-key" in cmd]
    assert len(send_key_calls) >= 3


def test_wezterm_send_enter_invalid_method_falls_back_to_auto(monkeypatch) -> None:
    """Invalid methods should behave like auto (try send-key then fall back)."""
    monkeypatch.setenv("CQ_WEZTERM_ENTER_METHOD", "bogus")
    monkeypatch.setattr(terminal, "_get_wezterm_bin", lambda: "/usr/bin/wezterm")
    monkeypatch.setattr(terminal.time, "sleep", lambda _: None)

    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        cmd = args[0]
        calls.append(cmd)
        if "send-key" in cmd:
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="nope")
        if "send-text" in cmd:
            assert kwargs.get("input") == b"\r"
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(terminal, "_run", fake_run)

    backend = terminal.WeztermBackend()
    backend._send_enter("123")

    assert any("send-key" in cmd for cmd in calls)
    assert any("send-text" in cmd for cmd in calls)


def test_wezterm_send_enter_key_mode_success(monkeypatch) -> None:
    """Key mode should early-return when send-key works."""
    monkeypatch.setenv("CQ_WEZTERM_ENTER_METHOD", "key")
    monkeypatch.setattr(terminal, "_get_wezterm_bin", lambda: "/usr/bin/wezterm")
    monkeypatch.setattr(terminal.time, "sleep", lambda _: None)

    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        cmd = args[0]
        calls.append(cmd)
        if "send-key" in cmd:
            return terminal.subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return terminal.subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unexpected")

    monkeypatch.setattr(terminal, "_run", fake_run)

    backend = terminal.WeztermBackend()
    backend._send_enter("123")

    assert any("send-key" in cmd for cmd in calls)
    assert not any("send-text" in cmd for cmd in calls)
