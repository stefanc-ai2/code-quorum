from __future__ import annotations

from pathlib import Path

import completion_hook


def test_notify_completion_passes_work_dir_to_hook(monkeypatch, tmp_path) -> None:
    captured: dict = {}

    def fake_run(cmd, *, input, capture_output, timeout, env=None, cwd=None, **_kwargs):
        captured["cmd"] = cmd
        captured["env"] = dict(env or {})
        captured["cwd"] = cwd

        class Result:
            returncode = 0

        return Result()

    # Force hook enabled.
    monkeypatch.setenv("CCB_COMPLETION_HOOK_ENABLED", "1")

    # Make completion_hook find our repo's ccb-completion-hook.
    monkeypatch.setattr(Path, "exists", lambda self: str(self).endswith("bin/ccb-completion-hook"))

    monkeypatch.setattr(completion_hook.subprocess, "run", fake_run)

    work_dir = str(tmp_path)
    completion_hook.notify_completion(
        provider="codex",
        output_file=None,
        reply="hello",
        req_id="abc",
        done_seen=True,
        caller="codex",
        work_dir=work_dir,
    )

    assert captured["env"]["CCB_WORK_DIR"] == work_dir
    assert captured["cwd"] == work_dir
