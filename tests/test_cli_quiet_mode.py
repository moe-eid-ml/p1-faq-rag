"""MC-KOS-25: Tests for CLI quiet mode."""

from unittest.mock import MagicMock



def _patch_pack(monkeypatch, overall_verdict="yellow", checks=None):
    if checks is None:
        checks = [
            {
                "check_id": "FakeChecker",
                "verdict": overall_verdict,
                "reason": "ko_phrase_found",
                "evidence": [{"doc_id": "doc.pdf", "page": 1, "snippet": "test"}],
            }
        ]
    mock_pack = MagicMock()
    mock_pack.to_dict.return_value = {
        "schema_version": "1.0",
        "overall_verdict": overall_verdict,
        "verdict": overall_verdict,
        "summary": "Test",
        "checks": checks,
    }

    import kosniper.cli
    monkeypatch.setattr(kosniper.cli, "make_evidence_pack", lambda *_, **__: mock_pack)


class TestCliQuietMode:
    """Tests for --quiet output suppression."""

    def test_quiet_suppresses_summary(self, monkeypatch, capsys):
        _patch_pack(monkeypatch)

        from kosniper.cli import main

        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test", "--quiet"])
        captured = capsys.readouterr()

        assert result == 0
        assert captured.err.strip() == ""

    def test_non_quiet_includes_summary(self, monkeypatch, capsys):
        _patch_pack(monkeypatch)

        from kosniper.cli import main

        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test"])
        captured = capsys.readouterr()

        assert result == 0
        assert "[YELLOW]" in captured.err

    def test_quiet_does_not_suppress_guard_errors(self, monkeypatch, capsys):
        _patch_pack(monkeypatch, overall_verdict="green", checks=[])

        from kosniper.cli import main

        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test", "--quiet"])
        captured = capsys.readouterr()

        assert result == 2
        assert "GREEN without evidence" in captured.err
