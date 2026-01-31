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

    # Simulate callers setting a preferred session from registry.
    reader.set_preferred_session(old_session)

    assert reader.latest_message() == "new"


def test_scan_includes_preferred_session_directory(tmp_path, monkeypatch) -> None:
    """
    When project_dir has no sessions and the preferred session is in a different
    directory, _scan_latest_session should fall back to scanning the preferred
    session's directory to find sessions there.
    """
    projects_root = tmp_path / "claude-projects"
    projects_root.mkdir()

    # Two different project directories
    project_a = projects_root / "project-a"
    project_a.mkdir()

    work_dir = tmp_path / "repo-b"
    work_dir.mkdir()

    # Create sessions only in project_a (project_dir for work_dir will be empty)
    old_session_a = project_a / "old.jsonl"
    new_session_a = project_a / "new.jsonl"
    _write_session(old_session_a, "old from A")
    _write_session(new_session_a, "new from A")

    # Make new_session_a the newest
    now = time.time()
    os.utime(old_session_a, (now - 20, now - 20))
    os.utime(new_session_a, (now, now))

    # Reader is initialized with work_dir that maps to an empty/non-existent project_dir
    # but preferred session points to old session in project_a
    reader = ClaudeLogReader(root=projects_root, work_dir=work_dir, use_sessions_index=False)
    reader.set_preferred_session(old_session_a)

    # Should find new_session_a because project_dir is empty, so it falls back
    # to scanning preferred session's directory
    assert reader.latest_message() == "new from A"


def test_scan_skips_confirmed_sidechain_sessions(tmp_path) -> None:
    """
    Sessions with isSidechain: true should be skipped in favor of older
    non-sidechain sessions.
    """
    projects_root = tmp_path / "claude-projects"
    projects_root.mkdir()

    work_dir = tmp_path / "repo"
    work_dir.mkdir()

    # Create a reader first to get the actual project_dir it will use
    reader = ClaudeLogReader(root=projects_root, work_dir=work_dir, use_sessions_index=False)
    project_dir = reader._project_dir()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create sessions: old non-sidechain, new sidechain
    old_session = project_dir / "old.jsonl"
    new_sidechain = project_dir / "new-sidechain.jsonl"

    # Old session: no isSidechain field (treated as non-sidechain candidate)
    old_session.write_text(
        json.dumps({"type": "assistant", "content": [{"type": "text", "text": "old main"}]}) + "\n",
        encoding="utf-8",
    )

    # New session: explicit isSidechain: true
    new_sidechain.write_text(
        json.dumps({"isSidechain": True}) + "\n"
        + json.dumps({"type": "assistant", "content": [{"type": "text", "text": "new sidechain"}]}) + "\n",
        encoding="utf-8",
    )

    now = time.time()
    os.utime(old_session, (now - 10, now - 10))
    os.utime(new_sidechain, (now, now))

    # Should return old_session because new_sidechain is confirmed sidechain
    assert reader.latest_message() == "old main"


def test_scan_prefers_project_dir_over_preferred_dir(tmp_path) -> None:
    """
    When project_dir has sessions, it should be used even if preferred session
    points to a different directory with newer sessions. This prevents cross-repo bleed.
    """
    projects_root = tmp_path / "claude-projects"
    projects_root.mkdir()

    work_dir = tmp_path / "repo"
    work_dir.mkdir()

    reader = ClaudeLogReader(root=projects_root, work_dir=work_dir, use_sessions_index=False)
    project_dir = reader._project_dir()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Different directory (simulating a different project)
    other_dir = projects_root / "other-project"
    other_dir.mkdir()

    # Session in project_dir
    project_session = project_dir / "project.jsonl"
    _write_session(project_session, "from project dir")

    # Newer session in other_dir
    other_session = other_dir / "other.jsonl"
    _write_session(other_session, "from other dir")

    now = time.time()
    os.utime(project_session, (now - 10, now - 10))
    os.utime(other_session, (now, now))  # newer

    # Set preferred session to point to the other directory
    reader.set_preferred_session(other_session)

    # Should still return from project_dir (not cross-repo bleed)
    assert reader.latest_message() == "from project dir"
