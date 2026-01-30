from __future__ import annotations


def get_backend_env() -> str | None:
    """Return backend environment override (Windows/WSL support removed)."""
    return None


def apply_backend_env() -> None:
    """No-op (Windows/WSL support removed)."""
    return

