from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from cli_output import atomic_write_text
from project_id import compute_cq_project_id
from session_scope import DEFAULT_SESSION, normalize_session_name
from terminal import get_backend_for_session

REGISTRY_PREFIX = "cq-session-"
REGISTRY_SUFFIX = ".json"
REGISTRY_TTL_SECONDS = 7 * 24 * 60 * 60


def _debug_enabled() -> bool:
    return os.environ.get("CQ_DEBUG") in ("1", "true", "yes")


def _debug(message: str) -> None:
    if not _debug_enabled():
        return
    print(f"[DEBUG] {message}", file=sys.stderr)


def _registry_dir() -> Path:
    return Path.home() / ".cq" / "run"


def _normalize_cq_session_name(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return DEFAULT_SESSION
    try:
        return normalize_session_name(raw)
    except ValueError:
        return DEFAULT_SESSION


def registry_path_for_session(session_id: str) -> Path:
    return _registry_dir() / f"{REGISTRY_PREFIX}{session_id}{REGISTRY_SUFFIX}"


def _iter_registry_files() -> Iterable[Path]:
    registry_dir = _registry_dir()
    if not registry_dir.exists():
        return []
    return sorted(registry_dir.glob(f"{REGISTRY_PREFIX}*{REGISTRY_SUFFIX}"))


def _coerce_updated_at(value: Any, fallback_path: Optional[Path] = None) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.isdigit():
            try:
                return int(trimmed)
            except ValueError:
                pass
    if fallback_path:
        try:
            return int(fallback_path.stat().st_mtime)
        except OSError:
            return 0
    return 0


def _is_stale(updated_at: int, now: Optional[int] = None) -> bool:
    if updated_at <= 0:
        return True
    now_ts = int(time.time()) if now is None else int(now)
    return (now_ts - updated_at) > REGISTRY_TTL_SECONDS


def _load_registry_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        _debug(f"Failed to read registry {path}: {exc}")
    return None


def _provider_entry_from_legacy(data: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """
    Best-effort migration from legacy flat keys to providers.<provider>.*
    """
    provider = (provider or "").strip().lower()
    out: Dict[str, Any] = {}

    if provider == "codex":
        for k_src, k_dst in [
            ("codex_pane_id", "pane_id"),
            ("pane_title_marker", "pane_title_marker"),
            ("codex_session_id", "codex_session_id"),
            ("codex_session_path", "codex_session_path"),
        ]:
            v = data.get(k_src)
            if v:
                out[k_dst] = v
    elif provider == "claude":
        v = data.get("claude_pane_id")
        if v:
            out["pane_id"] = v

    return out


def _get_providers_map(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    providers = data.get("providers")
    if isinstance(providers, dict):
        out: Dict[str, Dict[str, Any]] = {}
        for k, v in providers.items():
            if isinstance(k, str) and isinstance(v, dict):
                out[k.strip().lower()] = dict(v)
        return out

    # Legacy flat format: derive providers on demand (no persistence here).
    out = {}
    for p in ("codex", "claude"):
        entry = _provider_entry_from_legacy(data, p)
        if entry:
            out[p] = entry
    return out


def _provider_pane_alive(record: Dict[str, Any], provider: str) -> bool:
    providers = _get_providers_map(record)
    entry = providers.get((provider or "").strip().lower())
    if not isinstance(entry, dict):
        return False

    pane_id = str(entry.get("pane_id") or "").strip()
    marker = str(entry.get("pane_title_marker") or "").strip()

    backend = None
    try:
        backend = get_backend_for_session({"terminal": record.get("terminal", "tmux")})
    except Exception:
        backend = None
    if not backend:
        return False

    # Best-effort marker resolution if pane_id is missing/stale.
    if (not pane_id) and marker:
        resolver = getattr(backend, "find_pane_by_title_marker", None)
        if callable(resolver):
            try:
                pane_id = str(resolver(marker) or "").strip()
            except Exception:
                pane_id = ""

    if not pane_id:
        return False

    try:
        return bool(backend.is_alive(pane_id))
    except Exception:
        return False


def load_registry_by_session_id(
    session_id: str, session_name: str | None = None
) -> Optional[Dict[str, Any]]:
    if not session_id:
        return None
    path = registry_path_for_session(session_id)
    if not path.exists():
        return None
    data = _load_registry_file(path)
    if not data:
        return None
    if (session_name or "").strip():
        want = _normalize_cq_session_name(session_name)
        have = _normalize_cq_session_name(data.get("cq_session_name"))
        if have != want:
            return None
    updated_at = _coerce_updated_at(data.get("updated_at"), path)
    if _is_stale(updated_at):
        _debug(f"Registry stale for session {session_id}: {path}")
        return None
    return data


def load_registry_by_claude_pane(
    pane_id: str, session_name: str | None = None
) -> Optional[Dict[str, Any]]:
    if not pane_id:
        return None
    want_session = None
    if (session_name or "").strip():
        want_session = _normalize_cq_session_name(session_name)
    best: Optional[Dict[str, Any]] = None
    best_ts = -1
    for path in _iter_registry_files():
        data = _load_registry_file(path)
        if not data:
            continue
        if want_session is not None:
            have = _normalize_cq_session_name(data.get("cq_session_name"))
            if have != want_session:
                continue
        providers = _get_providers_map(data)
        claude = providers.get("claude") if isinstance(providers, dict) else None
        claude_pane = (claude or {}).get("pane_id") if isinstance(claude, dict) else None
        if (claude_pane or data.get("claude_pane_id")) != pane_id:
            continue
        updated_at = _coerce_updated_at(data.get("updated_at"), path)
        if _is_stale(updated_at):
            _debug(f"Registry stale for pane {pane_id}: {path}")
            continue
        if updated_at > best_ts:
            best = data
            best_ts = updated_at
    return best


def load_registry_by_project_id(
    cq_project_id: str, provider: str, session_name: str | None = None
) -> Optional[Dict[str, Any]]:
    """
    Load the newest alive registry record matching `{cq_project_id, provider, session_name}`.

    This enforces directory isolation and avoids parent-directory pollution.
    """
    proj = (cq_project_id or "").strip()
    prov = (provider or "").strip().lower()
    if not proj or not prov:
        return None

    want_session = None
    if (session_name or "").strip():
        want_session = _normalize_cq_session_name(session_name)

    best: Optional[Dict[str, Any]] = None
    best_ts = -1
    best_needs_migration = False

    for path in _iter_registry_files():
        data = _load_registry_file(path)
        if not data:
            continue
        updated_at = _coerce_updated_at(data.get("updated_at"), path)
        if _is_stale(updated_at):
            continue

        if want_session is not None:
            have = _normalize_cq_session_name(data.get("cq_session_name"))
            if have != want_session:
                continue

        existing = (data.get("cq_project_id") or "").strip()
        inferred = ""
        if not existing:
            # Back-compat: infer from work_dir (no side effects while scanning).
            wd = (data.get("work_dir") or "").strip()
            if wd:
                try:
                    inferred = compute_cq_project_id(Path(wd))
                except Exception:
                    inferred = ""
        effective = existing or inferred

        if effective != proj:
            continue

        if not _provider_pane_alive(data, prov):
            continue

        # Prefer the newest record for this project+provider.
        if updated_at > best_ts:
            best = data
            best_ts = updated_at
            best_needs_migration = (not existing) and bool(inferred)

    if best and best_needs_migration:
        # Best-effort persistence: update only the winning record to include cq_project_id.
        try:
            if not (best.get("cq_project_id") or "").strip():
                wd = (best.get("work_dir") or "").strip()
                if wd:
                    best["cq_project_id"] = compute_cq_project_id(Path(wd))
                    upsert_registry(best)
        except Exception:
            pass

    return best


def load_registry_by_project_id_unfiltered(
    cq_project_id: str, provider: str, session_name: str | None = None
) -> Optional[Dict[str, Any]]:
    """
    Load the newest registry record matching `{cq_project_id, provider, session_name}` without requiring pane liveness.

    Useful as a fallback when the registry is present but the pane has been closed/restarted.
    """
    proj = (cq_project_id or "").strip()
    prov = (provider or "").strip().lower()
    if not proj or not prov:
        return None

    want_session = None
    if (session_name or "").strip():
        want_session = _normalize_cq_session_name(session_name)

    best: Optional[Dict[str, Any]] = None
    best_ts = -1

    for path in _iter_registry_files():
        data = _load_registry_file(path)
        if not data:
            continue
        updated_at = _coerce_updated_at(data.get("updated_at"), path)
        if _is_stale(updated_at):
            continue

        if want_session is not None:
            have = _normalize_cq_session_name(data.get("cq_session_name"))
            if have != want_session:
                continue

        existing = (data.get("cq_project_id") or "").strip()
        inferred = ""
        if not existing:
            wd = (data.get("work_dir") or "").strip()
            if wd:
                try:
                    inferred = compute_cq_project_id(Path(wd))
                except Exception:
                    inferred = ""
        effective = existing or inferred
        if effective != proj:
            continue

        if prov not in _get_providers_map(data):
            continue

        if updated_at > best_ts:
            best = data
            best_ts = updated_at

    return best


def upsert_registry(record: Dict[str, Any]) -> bool:
    session_id = record.get("cq_session_id")
    if not session_id:
        _debug("Registry update skipped: missing cq_session_id")
        return False
    path = registry_path_for_session(str(session_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Best-effort: keep registry files private (they contain pane ids/session paths).
    try:
        os.chmod(path.parent, 0o700)
    except Exception:
        pass

    data: Dict[str, Any] = {}
    if path.exists():
        existing = _load_registry_file(path)
        if isinstance(existing, dict):
            data.update(existing)

    # Normalize to the new schema.
    providers = _get_providers_map(data)

    # Accept either a nested providers dict, or legacy flat keys, or explicit provider.
    incoming_providers = record.get("providers")
    if isinstance(incoming_providers, dict):
        for p, entry in incoming_providers.items():
            if not isinstance(p, str) or not isinstance(entry, dict):
                continue
            key = p.strip().lower()
            providers.setdefault(key, {})
            for k, v in entry.items():
                if v is None:
                    continue
                providers[key][k] = v

    provider = record.get("provider")
    if isinstance(provider, str) and provider.strip():
        p = provider.strip().lower()
        providers.setdefault(p, {})
        for k, v in record.items():
            if v is None:
                continue
            if k in {"provider", "providers"}:
                continue
            # Provider-scoped keys should be passed in nested form by new code.
            if (
                k in {"pane_id", "pane_title_marker"}
                or k.endswith("_session_id")
                or k.endswith("_session_path")
                or k.endswith("_project_id")
            ):
                providers[p][k] = v

    # Migrate legacy flat fields into providers.
    for p in ("codex", "claude"):
        legacy_entry = _provider_entry_from_legacy(record, p)
        if legacy_entry:
            providers.setdefault(p, {})
            providers[p].update({k: v for k, v in legacy_entry.items() if v is not None})

    # Top-level fields.
    for key, value in record.items():
        if value is None:
            continue
        if key in {"providers", "provider"}:
            continue
        # Legacy provider-scoped keys stay duplicated for compatibility but won't be used for routing.
        data[key] = value

    data["providers"] = providers

    # Ensure cq_project_id exists (best-effort from work_dir).
    if not (data.get("cq_project_id") or "").strip():
        wd = (data.get("work_dir") or "").strip()
        if wd:
            try:
                data["cq_project_id"] = compute_cq_project_id(Path(wd))
            except Exception:
                pass

    data["updated_at"] = int(time.time())

    try:
        atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        return True
    except Exception as exc:
        _debug(f"Failed to write registry {path}: {exc}")
        return False
