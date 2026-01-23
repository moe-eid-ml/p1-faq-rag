"""MC-KOS-48: Verify receipt tests.

Tests: 3 including 1 adversarial per Sniper process rules.
- test_receipt_written_on_success
- test_receipt_not_written_on_failure
- test_adversarial_receipt_write_error_fails_closed
"""

import json
import subprocess
import sys


class TestVerifyReceipt:
    """Tests for verify receipt functionality."""

    def test_receipt_written_on_success(self, tmp_path):
        """Success + --receipt writes verify_receipt.json with expected keys."""
        # Create valid pack
        evidence_pack = {
            "overall_verdict": "abstain",
            "summary": "No findings",
            "checks": [],
        }
        with open(tmp_path / "evidence_pack.json", "w") as f:
            json.dump(evidence_pack, f)

        document_map = {
            "doc_id": "test.pdf",
            "offset_basis": "normalized_text_v1",
            "overall_sha256": "abc123def456",
        }
        with open(tmp_path / "document_map.json", "w") as f:
            json.dump(document_map, f)

        result = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--verify-pack", "--in-dir", str(tmp_path), "--receipt"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "OK" in result.stdout

        # Check receipt file exists and has expected keys
        receipt_path = tmp_path / "verify_receipt.json"
        assert receipt_path.exists(), "verify_receipt.json should be created"

        with open(receipt_path) as f:
            receipt = json.load(f)

        assert receipt["status"] == "ok"
        assert receipt["tool"] == "kosniper"
        assert "version" in receipt
        assert "checked_at" in receipt
        # Verify checked_at is ISO8601 format (contains T and timezone)
        assert "T" in receipt["checked_at"]
        assert receipt["in_dir"] == str(tmp_path)
        assert receipt["document_map_sha256"] == "abc123def456"

    def test_receipt_not_written_on_failure(self, tmp_path):
        """Failure + --receipt does NOT write verify_receipt.json (fail-closed)."""
        # Create invalid pack (missing document_map.json)
        evidence_pack = {
            "overall_verdict": "abstain",
            "checks": [],
        }
        with open(tmp_path / "evidence_pack.json", "w") as f:
            json.dump(evidence_pack, f)

        result = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--verify-pack", "--in-dir", str(tmp_path), "--receipt"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 2, "Should fail due to missing document_map.json"

        # Receipt file should NOT exist
        receipt_path = tmp_path / "verify_receipt.json"
        assert not receipt_path.exists(), "verify_receipt.json should NOT be created on failure"

    def test_adversarial_receipt_write_error_fails_closed(self, tmp_path):
        """ADVERSARIAL: Receipt write OSError => CLI exits 2, no partial file."""
        # Create valid pack
        evidence_pack = {
            "overall_verdict": "abstain",
            "summary": "No findings",
            "checks": [],
        }
        with open(tmp_path / "evidence_pack.json", "w") as f:
            json.dump(evidence_pack, f)

        document_map = {
            "doc_id": "test.pdf",
            "offset_basis": "normalized_text_v1",
            "overall_sha256": "abc123",
        }
        with open(tmp_path / "document_map.json", "w") as f:
            json.dump(document_map, f)

        # Create a directory named verify_receipt.json to cause OSError
        receipt_blocker = tmp_path / "verify_receipt.json"
        receipt_blocker.mkdir()

        result = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--verify-pack", "--in-dir", str(tmp_path), "--receipt"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
        assert "error" in result.stderr.lower() or "failed" in result.stderr.lower()

        # The blocker directory should still exist (no partial writes)
        assert receipt_blocker.is_dir(), "Blocker directory should remain"
