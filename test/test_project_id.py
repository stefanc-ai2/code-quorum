from __future__ import annotations

from pathlib import Path

import pytest

from project_id import compute_cq_project_id, normalize_work_dir


def test_normalize_work_dir_basic() -> None:
    result1 = normalize_work_dir("/a/b/../c")
    assert result1 == "/a/c"

    result2 = normalize_work_dir("/a//b///c")
    assert result2 == "/a/b/c"


def test_compute_cq_project_id_stable_for_same_dir(tmp_path: Path) -> None:
    pid1 = compute_cq_project_id(tmp_path)
    pid2 = compute_cq_project_id(tmp_path)
    assert pid1
    assert pid1 == pid2


def test_compute_cq_project_id_uses_anchor_root(tmp_path: Path) -> None:
    (tmp_path / ".cq_config").mkdir(parents=True, exist_ok=True)
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True, exist_ok=True)

    pid_root = compute_cq_project_id(tmp_path)
    pid_sub = compute_cq_project_id(subdir)
    assert pid_root
    assert pid_sub
    assert pid_root != pid_sub


def test_compute_cq_project_id_ignores_env_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    child = root / "sub"
    child.mkdir(parents=True, exist_ok=True)

    # No anchor: env var should not override current-dir isolation.
    monkeypatch.setenv("CQ_PROJECT_ROOT", str(root))
    pid_root = compute_cq_project_id(root)
    pid_child = compute_cq_project_id(child)
    assert pid_root
    assert pid_root != pid_child

    # Invalid env root should not crash.
    monkeypatch.setenv("CQ_PROJECT_ROOT", str(tmp_path / "does-not-exist"))
    assert compute_cq_project_id(child)


def test_compute_cq_project_id_fallback_diff_for_subdirs_without_anchor(tmp_path: Path) -> None:
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True, exist_ok=True)
    assert compute_cq_project_id(tmp_path) != compute_cq_project_id(subdir)
