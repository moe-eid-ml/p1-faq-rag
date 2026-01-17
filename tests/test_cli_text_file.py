"""MC-KOS-20: Tests for CLI --text-file mode.

Verifies:
1) --text-file produces same contract as --text
2) Adversarial: empty file triggers safe-fail (no false-green)
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run kosniper CLI with given args."""
    return subprocess.run(
        [sys.executable, "-m", "kosniper.cli"] + args,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


class TestCliTextFile:
    """Tests for --text-file mode."""

    def test_text_file_produces_valid_json(self):
        """--text-file produces valid EvidencePack JSON."""
        result = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text-file", str(SAMPLES_DIR / "tender_ko_phrase.txt"),
        ])

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert "schema_version" in data
        assert "overall_verdict" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_text_file_same_verdict_as_inline_text(self):
        """--text-file produces same verdict as equivalent --text."""
        # Read file content
        sample_file = SAMPLES_DIR / "tender_ko_phrase.txt"
        with open(sample_file, encoding="utf-8") as f:
            text_content = f.read()

        # Run with --text-file
        result_file = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text-file", str(sample_file),
        ])

        # Run with --text
        result_inline = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text", text_content,
        ])

        assert result_file.returncode == result_inline.returncode

        data_file = json.loads(result_file.stdout)
        data_inline = json.loads(result_inline.stdout)

        assert data_file["overall_verdict"] == data_inline["overall_verdict"]
        assert len(data_file["checks"]) == len(data_inline["checks"])

    def test_text_file_provenance_correct(self):
        """Evidence spans have correct doc_id and page from CLI args."""
        result = _run_cli([
            "--doc-id", "custom_doc.pdf",
            "--page", "42",
            "--text-file", str(SAMPLES_DIR / "tender_ko_phrase.txt"),
        ])

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        data = json.loads(result.stdout)
        for check in data["checks"]:
            for ev in check.get("evidence", []):
                assert ev["doc_id"] == "custom_doc.pdf"
                assert ev["page"] == 42

    def test_text_file_with_out_flag(self, tmp_path):
        """--out writes JSON to file instead of stdout."""
        out_file = tmp_path / "output.json"

        result = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text-file", str(SAMPLES_DIR / "tender_ko_phrase.txt"),
            "--out", str(out_file),
        ])

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert out_file.exists(), "Output file not created"

        # stdout should be empty (JSON goes to file)
        assert result.stdout.strip() == "", "stdout should be empty when --out is used"

        # File should contain valid JSON
        with open(out_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "overall_verdict" in data


class TestCliTextFileAdversarial:
    """Adversarial tests: proof-first invariants with --text-file."""

    def test_adversarial_empty_file_not_green(self, tmp_path):
        """ADVERSARIAL: Empty file must not yield GREEN without evidence."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        result = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text-file", str(empty_file),
        ])

        # Either exits with error OR produces non-green verdict with evidence
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # If it succeeds, must not be GREEN without checks
            if data["overall_verdict"] == "green":
                assert len(data["checks"]) > 0, "GREEN requires evidence"
            else:
                # Non-green is acceptable (ABSTAIN expected for empty)
                assert data["overall_verdict"] in ("yellow", "red", "abstain")

    def test_adversarial_neutral_text_rejects_false_green(self):
        """ADVERSARIAL: Neutral text triggers safe-fail (exit 2)."""
        result = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text-file", str(SAMPLES_DIR / "tender_neutral.txt"),
        ])

        # CLI rejects GREEN without evidence
        assert result.returncode == 2, (
            f"Expected exit 2 for GREEN without evidence, got {result.returncode}"
        )
        assert "GREEN without evidence" in result.stderr

    def test_adversarial_missing_file_error(self):
        """ADVERSARIAL: Missing file returns error, not crash."""
        result = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text-file", "/nonexistent/path/file.txt",
        ])

        assert result.returncode == 2, "Should return exit code 2 for file error"
        assert "Error" in result.stderr

    def test_adversarial_mutual_exclusion(self):
        """ADVERSARIAL: --text and --text-file together is rejected."""
        result = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text", "inline text",
            "--text-file", str(SAMPLES_DIR / "tender_ko_phrase.txt"),
        ])

        assert result.returncode == 2
        assert "mutually exclusive" in result.stderr
