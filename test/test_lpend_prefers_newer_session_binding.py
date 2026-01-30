from __future__ import annotations

import importlib.util
import json
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load_lpend(repo_root: Path):
    loader = SourceFileLoader("lpend_script", str(repo_root / "bin" / "lpend"))
    spec = importlib.util.spec_from_loader("lpend_script", loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_session(path: Path, message: str) -> None:
    payload = {"type": "assistant", "content": message}
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_lpend_prefers_newer_claude_session_path_over_registry(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    lpend = _load_lpend(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".ccb_config").mkdir(parents=True)

    old_path = tmp_path / "old.jsonl"
    new_path = tmp_path / "new.jsonl"
    _write_session(old_path, "old")
    _write_session(new_path, "new")

    now = time.time()
    # Make sure old_path is older.
    old_ts = now - 30
    new_ts = now
    old_path.touch()
    new_path.touch()
    import os

    os.utime(old_path, (old_ts, old_ts))
    os.utime(new_path, (new_ts, new_ts))

    # Force resolution to our tmp work dir, and inject both candidate paths.
    monkeypatch.setattr(lpend, "resolve_work_dir_with_registry", lambda *_args, **_kwargs: (work_dir, None))
    monkeypatch.setattr(lpend, "_load_registry_log_path", lambda *_args, **_kwargs: (old_path, {"stub": True}))
    monkeypatch.setattr(lpend, "_load_session_log_path", lambda *_args, **_kwargs: (new_path, "sid"))
    monkeypatch.setattr(lpend, "compute_ccb_project_id", lambda *_args, **_kwargs: "pid")

    class _FakeReader:
        def __init__(self, *args, **kwargs) -> None:
            self._preferred: Path | None = None

        def set_preferred_session(self, path: Path) -> None:
            self._preferred = path

        def latest_message(self) -> str | None:
            if not self._preferred:
                return None
            for line in self._preferred.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                msg = entry.get("content")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
            return None

        def latest_conversations(self, n: int):
            return []

    monkeypatch.setattr(lpend, "ClaudeLogReader", _FakeReader)

    rc = lpend.main(["lpend"])
    assert rc == lpend.EXIT_OK
    out = capsys.readouterr().out.strip()
    assert out == "new"


def test_lpend_prefers_session_with_newer_subagent_activity(tmp_path, monkeypatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    lpend = _load_lpend(repo_root)

    work_dir = tmp_path / "repo"
    (work_dir / ".ccb_config").mkdir(parents=True)

    registry_path = tmp_path / "registry.jsonl"
    session_path = tmp_path / "session.jsonl"
    _write_session(registry_path, "registry")
    _write_session(session_path, "session")

    now = time.time()
    # Make registry_path "older", but give it a newer subagent log mtime.
    registry_ts = now - 30
    session_ts = now - 10
    import os

    os.utime(registry_path, (registry_ts, registry_ts))
    os.utime(session_path, (session_ts, session_ts))

    subagents_dir = registry_path.parent / registry_path.stem / "subagents"
    subagents_dir.mkdir(parents=True)
    subagent_log = subagents_dir / "worker.jsonl"
    subagent_log.write_text('{"type":"assistant","content":"subagent"}\n', encoding="utf-8")
    os.utime(subagent_log, (now, now))

    monkeypatch.setattr(lpend, "resolve_work_dir_with_registry", lambda *_args, **_kwargs: (work_dir, None))
    monkeypatch.setattr(lpend, "_load_registry_log_path", lambda *_args, **_kwargs: (registry_path, {"stub": True}))
    monkeypatch.setattr(lpend, "_load_session_log_path", lambda *_args, **_kwargs: (session_path, "sid"))
    monkeypatch.setattr(lpend, "compute_ccb_project_id", lambda *_args, **_kwargs: "pid")

    class _FakeReader:
        def __init__(self, *args, **kwargs) -> None:
            self._preferred: Path | None = None

        def set_preferred_session(self, path: Path) -> None:
            self._preferred = path

        def latest_message(self) -> str | None:
            if not self._preferred:
                return None
            for line in self._preferred.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                msg = entry.get("content")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
            return None

        def latest_conversations(self, n: int):
            return []

    monkeypatch.setattr(lpend, "ClaudeLogReader", _FakeReader)

    rc = lpend.main(["lpend"])
    assert rc == lpend.EXIT_OK
    out = capsys.readouterr().out.strip()
    assert out == "registry"
