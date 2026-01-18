"""MC-KOS-26: CLI fail-closed verdict validation tests.

Verifies CLI rejects invalid/missing verdicts instead of defaulting to green.
"""

from unittest.mock import MagicMock


class TestCliVerdictValidation:
    """Tests for fail-closed verdict validation."""

    def test_valid_pack_passes_through(self, monkeypatch, capsys):
        """Happy path: valid pack with allowed verdicts passes."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "yellow",
            "verdict": "yellow",
            "summary": "Test",
            "checks": [
                {
                    "check_id": "TestChecker",
                    "verdict": "yellow",
                    "reason": "ko_phrase_found",
                    "evidence": [{"doc_id": "doc.pdf", "page": 1, "snippet": "test"}],
                }
            ],
        }

        def mock_make_evidence_pack(*args, **kwargs):
            return mock_pack

        import kosniper.cli
        monkeypatch.setattr(kosniper.cli, "make_evidence_pack", mock_make_evidence_pack)

        from kosniper.cli import main
        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test"])

        assert result == 0

    def test_adversarial_missing_overall_verdict_rejected(self, monkeypatch, capsys):
        """ADVERSARIAL: Missing overall_verdict rejected (exit 2)."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            # overall_verdict missing
            "verdict": "yellow",
            "summary": "Test",
            "checks": [],
        }

        def mock_make_evidence_pack(*args, **kwargs):
            return mock_pack

        import kosniper.cli
        monkeypatch.setattr(kosniper.cli, "make_evidence_pack", mock_make_evidence_pack)

        from kosniper.cli import main
        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test"])

        assert result == 2
        captured = capsys.readouterr()
        assert "Invalid or missing overall_verdict" in captured.err

    def test_adversarial_invalid_overall_verdict_rejected(self, monkeypatch, capsys):
        """ADVERSARIAL: Invalid overall_verdict string rejected (exit 2)."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "invalid_verdict",
            "verdict": "invalid_verdict",
            "summary": "Test",
            "checks": [],
        }

        def mock_make_evidence_pack(*args, **kwargs):
            return mock_pack

        import kosniper.cli
        monkeypatch.setattr(kosniper.cli, "make_evidence_pack", mock_make_evidence_pack)

        from kosniper.cli import main
        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test"])

        assert result == 2
        captured = capsys.readouterr()
        assert "Invalid or missing overall_verdict" in captured.err
        assert "invalid_verdict" in captured.err

    def test_adversarial_invalid_check_verdict_rejected(self, monkeypatch, capsys):
        """ADVERSARIAL: Invalid check verdict rejected (exit 2)."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "yellow",
            "verdict": "yellow",
            "summary": "Test",
            "checks": [
                {
                    "check_id": "TestChecker",
                    "verdict": "bad_verdict",  # Invalid
                    "reason": "ko_phrase_found",
                    "evidence": [{"doc_id": "doc.pdf", "page": 1, "snippet": "test"}],
                }
            ],
        }

        def mock_make_evidence_pack(*args, **kwargs):
            return mock_pack

        import kosniper.cli
        monkeypatch.setattr(kosniper.cli, "make_evidence_pack", mock_make_evidence_pack)

        from kosniper.cli import main
        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test"])

        assert result == 2
        captured = capsys.readouterr()
        assert "Invalid or missing verdict in check" in captured.err
        assert "bad_verdict" in captured.err
