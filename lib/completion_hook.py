"""
CCB Completion Hook - Async notification when CCB delegation tasks complete.

This module provides a function to notify Claude when a CCB task completes.
The notification is sent asynchronously to avoid blocking the daemon.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional


def env_bool(name: str, default: bool = True) -> bool:
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val not in ("0", "false", "no", "off")


def _run_hook_async(
    provider: str,
    output_file: Optional[str],
    reply: str,
    req_id: str,
    caller: str,
    *,
    work_dir: str | None = None,
) -> None:
    """Run the completion hook in a background thread."""
    if not env_bool("CCB_COMPLETION_HOOK_ENABLED", True):
        return

    def _run():
        try:
            # Find ccb-completion-hook script (Python script only, not .cmd wrapper)
            script_paths = [
                Path(__file__).parent.parent / "bin" / "ccb-completion-hook",
                Path.home() / ".local" / "bin" / "ccb-completion-hook",
                Path("/usr/local/bin/ccb-completion-hook"),
            ]
            # On Windows, check installed location (Python script, not .cmd)
            if os.name == "nt":
                localappdata = os.environ.get("LOCALAPPDATA", "")
                if localappdata:
                    # The actual Python script is in the bin folder without extension
                    script_paths.insert(0, Path(localappdata) / "codex-dual" / "bin" / "ccb-completion-hook")

            script = None
            for p in script_paths:
                if p.exists() and p.suffix not in (".cmd", ".bat"):
                    script = str(p)
                    break

            if not script:
                return

            # Use sys.executable to run the script (cross-platform, no shebang dependency)
            cmd = [
                sys.executable,
                script,
                "--provider", provider,
                "--caller", caller,
                "--req-id", req_id,
            ]
            if output_file:
                cmd.extend(["--output", output_file])

            env = os.environ.copy()
            cwd = None
            if work_dir:
                env["CCB_WORK_DIR"] = work_dir
                try:
                    if Path(work_dir).is_dir():
                        cwd = work_dir
                except Exception:
                    cwd = None

            # Pass reply via stdin to avoid command line length limits
            subprocess.run(
                cmd,
                input=(reply or "").encode("utf-8"),
                capture_output=True,
                timeout=10,
                env=env,
                cwd=cwd,
            )
        except Exception:
            pass

    thread = threading.Thread(target=_run, daemon=False)
    thread.start()
    thread.join(timeout=15)  # Wait for hook to complete


def notify_completion(
    provider: str,
    output_file: Optional[str],
    reply: str,
    req_id: str,
    done_seen: bool,
    caller: str = "claude",
    work_dir: str | None = None,
) -> None:
    """
    Notify the caller that a CCB delegation task has completed.

    Args:
        provider: Provider name (codex, gemini, opencode, droid)
        output_file: Path to the output file (if any)
        reply: The reply text from the provider
        req_id: The request ID
        done_seen: Whether the CCB_DONE signal was detected
        caller: Who initiated the request (claude, codex, droid)
    """
    if not done_seen:
        return

    _run_hook_async(provider, output_file, reply, req_id, caller, work_dir=work_dir)
