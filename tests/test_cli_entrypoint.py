"""MC-KOS-47: CLI entrypoint tests.

Tests: 3 including 1 adversarial per Sniper process rules.
- test_entrypoint_target_importable
- test_cli_help_works
- test_adversarial_bad_args_fails_closed
"""

import subprocess
import sys

from kosniper.cli import main


class TestCliEntrypoint:
    """Tests for CLI entrypoint wiring."""

    def test_entrypoint_target_importable(self):
        """Entrypoint target kosniper.cli:main is importable and callable."""
        # The entrypoint in pyproject.toml is: kosniper = "kosniper.cli:main"
        # Verify the target exists and is callable
        assert callable(main), "kosniper.cli:main must be callable"

        # Verify it returns an int (exit code) when called with --help
        # (argparse exits with 0 on --help, so we catch SystemExit)
        try:
            result = main(["--help"])
            # If it returns normally, it should be an int
            assert isinstance(result, int)
        except SystemExit as e:
            # --help causes SystemExit(0)
            assert e.code == 0

    def test_cli_help_works(self):
        """python -m kosniper.cli --help returns 0 and shows usage."""
        result = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "kosniper" in result.stdout.lower()

    def test_adversarial_bad_args_fails_closed(self):
        """ADVERSARIAL: Invalid args fail-closed with exit code 2 and error message."""
        result = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--nonexistent-flag"],
            capture_output=True,
            text=True,
        )
        # argparse returns exit code 2 for invalid arguments
        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
        assert "error" in result.stderr.lower() or "unrecognized" in result.stderr.lower()
