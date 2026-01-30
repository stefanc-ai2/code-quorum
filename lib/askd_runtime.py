from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path


def run_dir() -> Path:
    override = (os.environ.get("CCB_RUN_DIR") or "").strip()
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = (os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or "").strip()
        if base:
            return Path(base) / "ccb"
        return Path.home() / "AppData" / "Local" / "ccb"

    xdg_cache = (os.environ.get("XDG_CACHE_HOME") or "").strip()
    if xdg_cache:
        return Path(xdg_cache) / "ccb"
    return Path.home() / ".cache" / "ccb"


def state_file_path(name: str) -> Path:
    if name.endswith(".json"):
        return run_dir() / name
    return run_dir() / f"{name}.json"


def log_path(name: str) -> Path:
    if name.endswith(".log"):
        return run_dir() / name
    return run_dir() / f"{name}.log"

_LAST_LOG_SHRINK_CHECK: dict[str, float] = {}


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _maybe_shrink_log(path: Path) -> None:
    """
    Keep daemon logs from growing unbounded.

    Strategy: truncate to last N bytes when file exceeds `CCB_LOG_MAX_BYTES`.
    This preserves recent history while preventing disk bloat.
    """
    max_bytes = max(0, _env_int("CCB_LOG_MAX_BYTES", 2 * 1024 * 1024))  # 2 MiB default
    if max_bytes <= 0:
        return

    interval_s = max(0.0, float(_env_int("CCB_LOG_SHRINK_CHECK_INTERVAL_S", 10)))
    key = str(path)
    now = time.time()
    last = _LAST_LOG_SHRINK_CHECK.get(key, 0.0)
    if interval_s and (now - last) < interval_s:
        return
    _LAST_LOG_SHRINK_CHECK[key] = now

    try:
        st = path.stat()
        size = int(st.st_size)
    except Exception:
        return

    if size <= max_bytes:
        return

    try:
        with path.open("rb") as handle:
            handle.seek(-max_bytes, os.SEEK_END)
            tail = handle.read()
    except Exception:
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(tail)
            os.replace(tmp_name, path)
        finally:
            try:
                os.unlink(tmp_name)
            except Exception:
                pass
    except Exception:
        return


def write_log(path: Path, msg: str) -> None:
    try:
        _maybe_shrink_log(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Best-effort: keep daemon runtime dirs/logs private on multi-user systems.
        try:
            os.chmod(path.parent, 0o700)
        except Exception:
            pass

        # Best-effort secure create: ensure logs are not world-readable if umask is permissive.
        try:
            if not path.exists():
                fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            os.chmod(path, 0o600)
        except Exception:
            pass

        with path.open("a", encoding="utf-8") as handle:
            handle.write(msg.rstrip() + "\n")
    except Exception:
        pass


def random_token() -> str:
    return os.urandom(16).hex()


def normalize_connect_host(host: str) -> str:
    host = (host or "").strip()
    if not host or host in ("0.0.0.0",):
        return "127.0.0.1"
    if host in ("::", "[::]"):
        return "::1"
    return host
