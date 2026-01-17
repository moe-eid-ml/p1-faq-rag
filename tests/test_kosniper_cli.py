"""MC-KOS-13: Tests for KO scanner CLI.

Tests use subprocess to invoke the CLI as a black-box executable.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


class TestCliBasicUsage:
    """Tests for basic CLI functionality."""

    def test_cli_with_text_argument_returns_valid_json(self):
        """CLI with --text returns valid EvidencePack JSON."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kosniper.cli",
                "--doc-id",
                "test.pdf",
                "--page",
                "5",
                "--text",
                "Der Mindestumsatz beträgt 500.000 EUR.",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        assert "schema_version" in data
        assert "overall_verdict" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_cli_with_text_file_argument(self):
        """CLI with --text-file reads from file and returns valid JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Der Mindestumsatz beträgt 500.000 EUR.")
            temp_path = f.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kosniper.cli",
                    "--doc-id",
                    "uploaded.pdf",
                    "--page",
                    "1",
                    "--text-file",
                    temp_path,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}"

            data = json.loads(result.stdout)
            assert "schema_version" in data
            assert "overall_verdict" in data
            assert "checks" in data
        finally:
            Path(temp_path).unlink()

    def test_cli_outputs_summary_to_stderr(self):
        """CLI outputs human-readable summary to stderr."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kosniper.cli",
                "--doc-id",
                "doc.pdf",
                "--page",
                "1",
                "--text",
                "Der Mindestumsatz beträgt 500.000 EUR.",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "[GREEN]" in result.stderr or "[YELLOW]" in result.stderr or "[RED]" in result.stderr or "[ABSTAIN]" in result.stderr
        assert "check(s)" in result.stderr


class TestCliMissingArgs:
    """Tests for missing required arguments."""

    def test_missing_doc_id_exits_nonzero(self):
        """Missing --doc-id exits with code 2."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kosniper.cli",
                "--page",
                "1",
                "--text",
                "Some text",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0

    def test_missing_page_exits_nonzero(self):
        """Missing --page exits with code 2."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kosniper.cli",
                "--doc-id",
                "doc.pdf",
                "--text",
                "Some text",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0

    def test_missing_text_input_exits_with_code_2(self):
        """Missing both --text and --text-file exits with code 2."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kosniper.cli",
                "--doc-id",
                "doc.pdf",
                "--page",
                "1",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 2
        assert "required" in result.stderr.lower()

    def test_both_text_and_text_file_exits_with_code_2(self):
        """Providing both --text and --text-file exits with code 2."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kosniper.cli",
                "--doc-id",
                "doc.pdf",
                "--page",
                "1",
                "--text",
                "inline text",
                "--text-file",
                "file.txt",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 2
        assert "mutually exclusive" in result.stderr.lower()


class TestCliAdversarial:
    """Adversarial tests for proof-first safety."""

    def test_adversarial_empty_text_not_green(self):
        """ADVERSARIAL: Empty text must not yield GREEN verdict.

        Empty input provides no evidence of compliance; safe-fail requires
        non-GREEN (ABSTAIN/YELLOW/RED) to prevent false-green.
        """
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kosniper.cli",
                "--doc-id",
                "empty.pdf",
                "--page",
                "1",
                "--text",
                "",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        verdict = data.get("overall_verdict", "")
        assert verdict != "green", f"Empty text must not yield GREEN, got: {verdict}"

        # Non-neutral results must include evidence
        if verdict in ("red", "yellow", "abstain"):
            checks = data.get("checks", [])
            assert len(checks) > 0, "Non-green verdict requires at least one check result"
            for check in checks:
                if check.get("verdict") != "green":
                    assert len(check.get("evidence", [])) > 0, (
                        f"Non-green check {check.get('check_id')} must have evidence"
                    )
