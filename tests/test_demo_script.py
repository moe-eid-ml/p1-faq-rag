"""MC-KOS-19: Test for demo.sh script.

Verifies the one-command demo runner produces valid evidence pack JSON.
"""

import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
DEMO_SCRIPT = PROJECT_ROOT / "scripts" / "demo.sh"


class TestDemoScript:
    """Tests for scripts/demo.sh."""

    def test_demo_produces_valid_evidence_pack(self, tmp_path, monkeypatch):
        """Demo script creates evidence_pack.json with required keys."""
        # Run demo.sh from temp directory
        monkeypatch.chdir(tmp_path)

        # Copy samples to temp dir (script expects samples/ relative to project root)
        # Instead, run from project root and check output there
        result = subprocess.run(
            ["bash", str(DEMO_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env={**os.environ, "DISABLE_SEMANTIC": "1"},
        )

        assert result.returncode == 0, f"Demo failed: {result.stderr}"

        # Check evidence_pack.json was created
        output_file = PROJECT_ROOT / "evidence_pack.json"
        assert output_file.exists(), "evidence_pack.json not created"

        # Parse and validate JSON structure
        try:
            with open(output_file) as f:
                data = json.load(f)
        finally:
            # Cleanup
            output_file.unlink(missing_ok=True)

        assert "overall_verdict" in data, "Missing overall_verdict key"
        assert "checks" in data, "Missing checks key"
        assert isinstance(data["checks"], list), "checks must be a list"

    def test_demo_script_exists_and_executable(self):
        """Demo script exists and is executable."""
        assert DEMO_SCRIPT.exists(), f"Demo script not found: {DEMO_SCRIPT}"
        assert os.access(DEMO_SCRIPT, os.X_OK), "Demo script not executable"
