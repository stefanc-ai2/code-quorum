from __future__ import annotations

import json
import os
import time
from pathlib import Path

from claude_comm import ClaudeLogReader


def _write_session(path: Path, message: str) -> None:
    path.write_text(json.dumps({"type": "assistant", "content": [{"type": "text", "text": message}]}) + "\n", encoding="utf-8")


def test_latest_session_falls_back_to_scan_when_sessions_index_is_stale(tmp_path, monkeypatch) -> None:
    # Use a fake Claude projects root.
    projects_root = tmp_path / "claude-projects"
    projects_root.mkdir()

    # Create a fake work_dir under tmp so the key is stable.
    work_dir = tmp_path / "repo"
    work_dir.mkdir()

    monkeypatch.setenv("CLAUDE_PROJECTS_ROOT", str(projects_root))

    reader = ClaudeLogReader(root=projects_root, work_dir=work_dir, use_sessions_index=True)

    project_dir = reader._project_dir()
    project_dir.mkdir(parents=True, exist_ok=True)

    old_session = project_dir / "old.jsonl"
    new_session = project_dir / "new.jsonl"
    _write_session(old_session, "old")
    _write_session(new_session, "new")

    # Make sure new_session is newer on disk.
    now = time.time()
    os.utime(old_session, (now - 10, now - 10))
    os.utime(new_session, (now, now))

    # sessions-index.json points at the older session (stale/incomplete index).
    (project_dir / "sessions-index.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "fullPath": str(old_session),
                        "fileMtime": int((now - 10) * 1000),
                        "isSidechain": False,
                        "projectPath": str(work_dir),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    # Simulate callers (lpend / askd) setting a preferred session from registry.
    reader.set_preferred_session(old_session)

    assert reader.latest_message() == "new"

