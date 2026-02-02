from __future__ import annotations

import hashlib
import os
import posixpath
from pathlib import Path


def normalize_work_dir(value: str | Path) -> str:
    """
    Normalize a work_dir into a stable string for hashing and matching.

    Goals:
    - Be stable within a single environment (macOS/Linux).
    - Reduce trivial path-format mismatches (slashes, dot segments).
    """
    raw = str(value).strip()
    if not raw:
        return ""

    # Expand "~" early.
    if raw.startswith("~"):
        try:
            raw = os.path.expanduser(raw)
        except Exception:
            pass

    # Absolutize when relative (best-effort).
    try:
        p = Path(raw)
        if not p.is_absolute():
            raw = str((Path.cwd() / p).absolute())
    except Exception:
        pass

    s = raw.replace("\\", "/")

    # Collapse redundant separators and dot segments using POSIX semantics (we forced "/").
    if s.startswith("//"):
        prefix = "//"
        rest = posixpath.normpath(s[2:])
        s = prefix + rest.lstrip("/")
    else:
        s = posixpath.normpath(s)

    return s


def _find_cq_config_root(start_dir: Path) -> Path | None:
    """
    Find a `.cq_config/` directory in the current working directory only.

    This enforces per-directory isolation (no ancestor traversal).
    """
    try:
        current = Path(start_dir).expanduser().absolute()
    except Exception:
        current = Path.cwd()
    try:
        cfg = current / ".cq_config"
        if cfg.is_dir():
            return current
    except Exception:
        return None
    return None


def compute_cq_project_id(work_dir: Path) -> str:
    """
    Compute CQ's routing project id (cq_project_id).

    Priority:
    - Current directory containing `.cq_config/` (project anchor).
    - Current work_dir (fallback).
    """
    try:
        wd = Path(work_dir).expanduser().absolute()
    except Exception:
        wd = Path.cwd()

    # Priority 1: Current directory `.cq_config/` only
    base = _find_cq_config_root(wd)

    if base is None:
        base = wd

    norm = normalize_work_dir(base)
    if not norm:
        norm = normalize_work_dir(wd)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()
