"""MC-KOS-49: Demo pack script tests.

Tests: 2 including 1 adversarial per Sniper process rules.
- test_dry_run_prints_commands_and_exits_0
- test_adversarial_missing_pdf_fails_closed_exit_2
"""

import subprocess
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "demo_pack.sh"


def test_dry_run_prints_commands_and_exits_0(tmp_path):
    """--dry-run prints commands without executing and exits 0."""
    fake_pdf = "/path/to/fake.pdf"
    out_dir = str(tmp_path / "output")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), fake_pdf, "--out-dir", out_dir, "--dry-run"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"
    assert "--scan" in result.stdout
    assert "--verify-pack" in result.stdout
    assert "--receipt" in result.stdout
    assert out_dir in result.stdout


def test_adversarial_missing_pdf_fails_closed_exit_2():
    """ADVERSARIAL: Missing PDF file fails-closed with exit 2."""
    nonexistent_pdf = "/nonexistent/does-not-exist.pdf"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), nonexistent_pdf],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
    stderr_lower = result.stderr.lower()
    assert "pdf not found" in stderr_lower or "error" in stderr_lower
