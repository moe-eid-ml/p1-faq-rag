"""MC-KOS-22: Tests for CLI contradiction guard.

Verifies CLI blocks contradictory outputs where check verdict is worse than overall.
"""

from unittest.mock import MagicMock


class TestCliContradictionGuard:
    """Tests for CLI contradiction detection at boundary."""

    def test_contradiction_green_overall_red_check_blocked(self, monkeypatch):
        """CLI blocks contradictory output: overall=green but check=red."""
        # Create a mock pack that returns contradictory data
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "green",
            "verdict": "green",
            "summary": "Contradictory",
            "checks": [
                {
                    "check_id": "FakeChecker",
                    "verdict": "red",
                    "reason": "below_threshold",
                    "evidence": [{"doc_id": "doc.pdf", "page": 1, "snippet": "test"}],
                }
            ],
        }

        def mock_make_evidence_pack(*args, **kwargs):
            return mock_pack

        # Monkeypatch at module level
        import kosniper.cli
        monkeypatch.setattr(kosniper.cli, "make_evidence_pack", mock_make_evidence_pack)

        # Run CLI
        from kosniper.cli import main
        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test"])

        assert result == 2

    def test_contradiction_green_overall_yellow_check_blocked(self, monkeypatch):
        """CLI blocks contradictory output: overall=green but check=yellow."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "green",
            "verdict": "green",
            "summary": "Contradictory",
            "checks": [
                {
                    "check_id": "FakeChecker",
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

        assert result == 2

    def test_contradiction_yellow_overall_red_check_blocked(self, monkeypatch):
        """CLI blocks contradictory output: overall=yellow but check=red."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "yellow",
            "verdict": "yellow",
            "summary": "Contradictory",
            "checks": [
                {
                    "check_id": "FakeChecker",
                    "verdict": "red",
                    "reason": "below_threshold",
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

    def test_valid_pack_passes_through(self, monkeypatch):
        """Valid pack (overall matches worst check) passes through."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "yellow",
            "verdict": "yellow",
            "summary": "Valid",
            "checks": [
                {
                    "check_id": "FakeChecker",
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


class TestCliContradictionGuardStderr:
    """Tests that contradiction guard prints clear error to stderr."""

    def test_contradiction_error_message_in_stderr(self, monkeypatch, capsys):
        """Contradiction error message appears in stderr."""
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "green",
            "verdict": "green",
            "summary": "Contradictory",
            "checks": [
                {
                    "check_id": "FakeChecker",
                    "verdict": "red",
                    "reason": "below_threshold",
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

        captured = capsys.readouterr()
        assert result == 2
        assert "Contradictory output" in captured.err
        assert "red" in captured.err
        assert "green" in captured.err
