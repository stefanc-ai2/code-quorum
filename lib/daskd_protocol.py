from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from ccb_protocol import (
    DONE_PREFIX,
    REQ_ID_PREFIX,
    is_done_text,
    make_req_id,
    strip_done_text,
)

ANY_DONE_LINE_RE = re.compile(r"^\s*CCB_DONE:\s*\d{8}-\d{6}-\d{3}-\d+\s*$", re.IGNORECASE)
_SKILL_CACHE: str | None = None


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    val = raw.strip().lower()
    if val in {"0", "false", "no", "off"}:
        return False
    if val in {"1", "true", "yes", "on"}:
        return True
    return default


def _load_droid_skills() -> str:
    global _SKILL_CACHE
    if _SKILL_CACHE is not None:
        return _SKILL_CACHE
    if not _env_bool("CCB_DROID_SKILLS", True):
        _SKILL_CACHE = ""
        return _SKILL_CACHE
    skills_dir = Path(__file__).resolve().parent.parent / "droid_skills"
    if not skills_dir.is_dir():
        _SKILL_CACHE = ""
        return _SKILL_CACHE
    parts: list[str] = []
    for name in ("cask.md", "gask.md", "lask.md", "oask.md"):
        path = skills_dir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if text:
            parts.append(text)
    _SKILL_CACHE = "\n\n".join(parts).strip()
    return _SKILL_CACHE


def wrap_droid_prompt(message: str, req_id: str) -> str:
    message = (message or "").rstrip()
    skills = _load_droid_skills()
    if skills:
        message = f"{skills}\n\n{message}".strip()
    return (
        f"{REQ_ID_PREFIX} {req_id}\n\n"
        f"{message}\n\n"
        "IMPORTANT:\n"
        "- Reply with an execution summary, in English. Do not stay silent.\n"
        "- End your reply with this exact final line (verbatim, on its own line):\n"
        f"{DONE_PREFIX} {req_id}\n"
    )


def extract_reply_for_req(text: str, req_id: str) -> str:
    """
    Extract the reply segment for req_id from a Droid message.

    Droid may emit multiple replies in a single assistant message, each ending with its own
    `CCB_DONE: <req_id>` line. In that case, we want only the segment between the previous done line
    (any req_id) and the done line for our req_id.
    """
    lines = [ln.rstrip("\n") for ln in (text or "").splitlines()]
    if not lines:
        return ""

    target_re = re.compile(rf"^\s*CCB_DONE:\s*{re.escape(req_id)}\s*$", re.IGNORECASE)
    done_idxs = [i for i, ln in enumerate(lines) if ANY_DONE_LINE_RE.match(ln or "")]
    target_idxs = [i for i in done_idxs if target_re.match(lines[i] or "")]

    if not target_idxs:
        return strip_done_text(text, req_id)

    target_i = target_idxs[-1]
    prev_done_i = -1
    for i in reversed(done_idxs):
        if i < target_i:
            prev_done_i = i
            break

    segment = lines[prev_done_i + 1 : target_i]
    while segment and segment[0].strip() == "":
        segment = segment[1:]
    while segment and segment[-1].strip() == "":
        segment = segment[:-1]
    return "\n".join(segment).rstrip()


@dataclass(frozen=True)
class DaskdRequest:
    client_id: str
    work_dir: str
    timeout_s: float
    quiet: bool
    message: str
    output_path: str | None = None
    req_id: str | None = None
    caller: str = "claude"


@dataclass(frozen=True)
class DaskdResult:
    exit_code: int
    reply: str
    req_id: str
    session_key: str
    done_seen: bool
    done_ms: int | None = None
