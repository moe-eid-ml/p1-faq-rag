"""MC-KOS-46: Verify pack tests.

Tests: 5 including 1 adversarial per Sniper process rules.
- test_happy_path_valid_pack
- test_missing_required_file_fails
- test_adversarial_missing_offset_basis_fails
- test_false_green_without_evidence_fails
- test_cli_verify_pack
"""

import json
import subprocess
import sys

import pytest

from kosniper.verify import verify_pack


class TestVerifyPack:
    """Tests for verify_pack function."""

    def test_happy_path_valid_pack(self, tmp_path):
        """Happy path: minimal valid export pack passes verification."""
        # Create valid evidence_pack.json
        evidence_pack = {
            "schema_version": "1.0",
            "overall_verdict": "red",
            "summary": "Hard KO detected",
            "checks": [
                {
                    "check_id": "MinimalKoPhraseChecker",
                    "verdict": "red",
                    "reason": "ko_phrase_detected",
                    "evidence": [
                        {
                            "doc_id": "test.pdf",
                            "page": 1,
                            "snippet": "Ausschlusskriterium",
                            "start_offset": 100,
                            "end_offset": 120,
                            "offset_basis": "normalized_text_v1",
                        }
                    ],
                }
            ],
        }
        with open(tmp_path / "evidence_pack.json", "w") as f:
            json.dump(evidence_pack, f)

        # Create valid document_map.json
        document_map = {
            "doc_id": "test.pdf",
            "offset_basis": "normalized_text_v1",
            "pages": [{"page_number": 1}],
            "overall_sha256": "abc123def456" * 5 + "abcd",  # 64 chars
        }
        with open(tmp_path / "document_map.json", "w") as f:
            json.dump(document_map, f)

        ok, msg = verify_pack(str(tmp_path))
        assert ok is True
        assert msg == "OK"

    @pytest.mark.parametrize("missing_file", ["evidence_pack.json", "document_map.json"])
    def test_missing_required_file_fails(self, tmp_path, missing_file):
        """Missing required file fails verification."""
        if missing_file == "evidence_pack.json":
            document_map = {
                "doc_id": "test.pdf",
                "offset_basis": "normalized_text_v1",
                "overall_sha256": "abc123",
            }
            with open(tmp_path / "document_map.json", "w") as f:
                json.dump(document_map, f)
        else:
            evidence_pack = {
                "overall_verdict": "abstain",
                "checks": [],
            }
            with open(tmp_path / "evidence_pack.json", "w") as f:
                json.dump(evidence_pack, f)

        ok, msg = verify_pack(str(tmp_path))
        assert ok is False
        assert missing_file in msg

    def test_adversarial_missing_offset_basis_fails(self, tmp_path):
        """ADVERSARIAL: Evidence with offsets but missing offset_basis fails."""
        # Create evidence_pack with offsets but no offset_basis
        evidence_pack = {
            "overall_verdict": "red",
            "checks": [
                {
                    "check_id": "TestChecker",
                    "verdict": "red",
                    "evidence": [
                        {
                            "doc_id": "test.pdf",
                            "page": 1,
                            "snippet": "KO phrase",
                            "start_offset": 100,
                            "end_offset": 120,
                            # Missing offset_basis!
                        }
                    ],
                }
            ],
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

        ok, msg = verify_pack(str(tmp_path))
        assert ok is False
        assert "offset_basis" in msg
        assert "normalized_text_v1" in msg

    def test_false_green_without_evidence_fails(self, tmp_path):
        """GREEN verdict without evidence fails (false-green prevention)."""
        evidence_pack = {
            "overall_verdict": "green",
            "checks": [],  # No checks = no evidence
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

        ok, msg = verify_pack(str(tmp_path))
        assert ok is False
        assert "False-green" in msg


class TestVerifyPackCLI:
    """Tests for --verify-pack CLI command."""

    @pytest.mark.parametrize(
        "with_in_dir, expected_code, expected_text",
        [(True, 0, "OK"), (False, 2, "--in-dir")],
    )
    def test_cli_verify_pack(self, tmp_path, with_in_dir, expected_code, expected_text):
        """CLI --verify-pack handles valid and missing input cases."""
        cmd = [sys.executable, "-m", "kosniper.cli", "--verify-pack"]

        if with_in_dir:
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

            cmd.extend(["--in-dir", str(tmp_path)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        assert result.returncode == expected_code
        if expected_code == 0:
            assert expected_text in result.stdout
        else:
            assert expected_text in result.stderr
