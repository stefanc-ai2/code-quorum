from __future__ import annotations

from pathlib import Path

import pytest

import session_scope
import session_utils


def test_resolve_session_name_defaults_to_default() -> None:
    assert session_scope.resolve_session_name(None, env={}) == session_scope.DEFAULT_SESSION


def test_resolve_session_name_reads_env_and_normalizes() -> None:
    assert session_scope.resolve_session_name(None, env={"CQ_SESSION": "Feature-X"}) == "feature-x"


def test_resolve_session_name_explicit_overrides_env() -> None:
    assert (
        session_scope.resolve_session_name("B", env={"CQ_SESSION": "a"})
        == "b"
    )


def test_resolve_session_name_invalid_env_falls_back() -> None:
    assert session_scope.resolve_session_name(None, env={"CQ_SESSION": "../oops"}) == "default"


def test_project_session_dir_default_vs_named(tmp_path: Path) -> None:
    assert session_scope.project_session_dir(tmp_path, "default") == tmp_path / ".cq_config"
    assert session_scope.project_session_dir(tmp_path, "feature-x") == tmp_path / ".cq_config" / "sessions" / "feature-x"


def test_find_project_session_file_prefers_named_session_then_falls_back(tmp_path: Path) -> None:
    cfg = tmp_path / ".cq_config"
    cfg.mkdir()
    default = cfg / ".codex-session"
    default.write_text("default", encoding="utf-8")

    # Named session missing -> fall back to default
    assert (
        session_scope.find_project_session_file(tmp_path, "feature-x", ".codex-session")
        == default
    )

    # Named session exists -> prefer it
    named_dir = cfg / "sessions" / "feature-x"
    named_dir.mkdir(parents=True)
    named = named_dir / ".codex-session"
    named.write_text("named", encoding="utf-8")

    assert (
        session_scope.find_project_session_file(tmp_path, "feature-x", ".codex-session")
        == named
    )


def test_session_utils_find_project_session_file_uses_session_or_env(tmp_path: Path) -> None:
    cfg = tmp_path / ".cq_config"
    cfg.mkdir()
    named_dir = cfg / "sessions" / "feature-x"
    named_dir.mkdir(parents=True)
    named = named_dir / ".claude-session"
    named.write_text("ok", encoding="utf-8")

    assert (
        session_utils.find_project_session_file(tmp_path, ".claude-session", session="feature-x")
        == named
    )
    assert (
        session_utils.find_project_session_file(tmp_path, ".claude-session", env={"CQ_SESSION": "feature-x"})
        == named
    )


def test_find_project_session_file_legacy_root_fallback(tmp_path: Path) -> None:
    legacy = tmp_path / ".codex-session"
    legacy.write_text("legacy", encoding="utf-8")
    assert session_scope.find_project_session_file(tmp_path, "default", ".codex-session") == legacy


def test_session_utils_rejects_invalid_explicit_session(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        session_utils.find_project_session_file(tmp_path, ".codex-session", session="../oops")


def test_session_utils_explicit_named_session_is_strict(tmp_path: Path) -> None:
    cfg = tmp_path / ".cq_config"
    cfg.mkdir()
    default = cfg / ".codex-session"
    default.write_text("default", encoding="utf-8")

    # Named session missing: do NOT fall back to default when session explicitly provided.
    assert (
        session_utils.find_project_session_file(tmp_path, ".codex-session", session="feature-x")
        is None
    )


def test_session_utils_env_named_session_allows_fallback(tmp_path: Path) -> None:
    cfg = tmp_path / ".cq_config"
    cfg.mkdir()
    default = cfg / ".codex-session"
    default.write_text("default", encoding="utf-8")

    # Named session missing: fall back to default when resolved via env (non-explicit).
    assert (
        session_utils.find_project_session_file(tmp_path, ".codex-session", env={"CQ_SESSION": "feature-x"})
        == default
    )


def test_find_project_session_file_strict_mode(tmp_path: Path) -> None:
    cfg = tmp_path / ".cq_config"
    cfg.mkdir()
    default = cfg / ".codex-session"
    default.write_text("default", encoding="utf-8")

    assert (
        session_scope.find_project_session_file(
            tmp_path, "feature-x", ".codex-session", strict=True
        )
        is None
    )
