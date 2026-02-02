from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def _read_version_from_cq(repo_root: Path) -> str:
    content = (repo_root / "cq").read_text(encoding="utf-8", errors="replace")
    m = re.search(
        r'^VERSION\s*=\s*["\']([^"\']+)["\']\s*$',
        content,
        flags=re.MULTILINE,
    )
    assert m, "Expected VERSION constant in cq script"
    return m.group(1)


def test_cq_print_version() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    expected = _read_version_from_cq(repo_root)

    result = subprocess.run(
        [sys.executable, str(repo_root / "cq"), "--print-version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"v{expected}"


def test_cq_mounted_reports_session(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    work_dir = tmp_path / "repo"
    (work_dir / ".cq_config").mkdir(parents=True, exist_ok=True)
    (work_dir / ".cq_config" / ".codex-session").write_text(
        json.dumps({}), encoding="utf-8"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "bin" / "cq-mounted"),
            str(work_dir),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["mounted"] == ["codex"]
