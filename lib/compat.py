"""Compatibility utilities (Unix-only)."""
from __future__ import annotations

import os
import sys

def setup_windows_encoding() -> None:
    """No-op (Windows is not supported)."""
    return


def decode_stdin_bytes(data: bytes) -> str:
    """Decode stdin bytes (Unix-only; Windows/mbcs handling removed)."""
    if not data:
        return ""

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16le", errors="replace")
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16be", errors="replace")

    forced = (os.environ.get("CQ_STDIN_ENCODING") or "").strip()
    if forced:
        return data.decode(forced, errors="replace")
    return data.decode("utf-8", errors="replace")


def read_stdin_text() -> str:
    """Read all text from stdin (non-interactive)."""
    try:
        buf = sys.stdin.buffer  # type: ignore[attr-defined]
    except Exception:
        # Fallback: whatever Python thinks stdin is.
        return sys.stdin.read()
    return decode_stdin_bytes(buf.read())
