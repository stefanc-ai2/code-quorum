from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping, Optional


DEFAULT_SESSION = "default"
SESSION_ENV_VAR = "CQ_SESSION"
SESSION_DIRNAME = "sessions"
PROJECT_CONFIG_DIRNAME = ".cq_config"

_SESSION_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def normalize_session_name(raw: str) -> str:
    name = (raw or "").strip().lower()
    if not name:
        raise ValueError("session name is empty")
    if name in {".", ".."}:
        raise ValueError("session name must not be '.' or '..'")
    if "/" in name or "\\" in name:
        raise ValueError("session name must not contain path separators")
    if not _SESSION_NAME_RE.fullmatch(name):
        raise ValueError(
            "invalid session name; use 1-64 chars: [a-z0-9][a-z0-9._-]*"
        )
    return name


def resolve_session_name(
    explicit: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """
    Resolve the active CQ session name.

    Precedence:
      1) explicit (e.g. --session)
      2) env[SESSION_ENV_VAR] (CQ_SESSION)
      3) DEFAULT_SESSION
    """
    candidate = (explicit or "").strip()
    if not candidate:
        if env is None:
            env = os.environ
        candidate = (env.get(SESSION_ENV_VAR) or "").strip()
    if not candidate:
        return DEFAULT_SESSION
    try:
        return normalize_session_name(candidate)
    except ValueError:
        # Be forgiving for env var corruption; explicit values should be validated by the caller.
        if explicit and explicit.strip():
            raise
        return DEFAULT_SESSION


def project_session_dir(work_dir: Path, session: str) -> Path:
    """
    Return the directory where session-scoped config files live.

    - default session: <work_dir>/.cq_config/
    - named session:   <work_dir>/.cq_config/sessions/<session>/
    """
    work_dir = Path(work_dir).resolve()
    session = normalize_session_name(session)
    cfg = work_dir / PROJECT_CONFIG_DIRNAME
    if session == DEFAULT_SESSION:
        return cfg
    return cfg / SESSION_DIRNAME / session


def find_project_session_file(
    work_dir: Path,
    session: str,
    filename: str,
    *,
    strict: bool = False,
) -> Optional[Path]:
    """
    Find a session file for `session` in `work_dir`.

    Lookup is local-only (no upward traversal) and backward compatible:
      1) <work_dir>/.cq_config/sessions/<session>/<filename>  (non-default sessions)
      2) <work_dir>/.cq_config/<filename>                    (default/legacy)
      3) <work_dir>/<filename>                               (legacy)

    If `strict=True` and `session` is non-default, only (1) is checked. This prevents
    accidentally routing an explicit named session to the default session's files.
    """
    work_dir = Path(work_dir).resolve()
    filename = str(filename or "").strip()
    if not filename:
        return None

    session = normalize_session_name(session)

    # 1) Session-scoped path (non-default sessions)
    if session != DEFAULT_SESSION:
        candidate = project_session_dir(work_dir, session) / filename
        if candidate.exists():
            return candidate
        if strict:
            return None

    # 2) Default session path (.cq_config/)
    default_candidate = project_session_dir(work_dir, DEFAULT_SESSION) / filename
    if default_candidate.exists():
        return default_candidate

    # 3) Legacy root dotfile
    legacy = work_dir / filename
    if legacy.exists():
        return legacy

    return None
