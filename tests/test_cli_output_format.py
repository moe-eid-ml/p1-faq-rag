"""MC-KOS-24: Tests for CLI output format flag."""

from unittest.mock import MagicMock

import pytest


class TestCliOutputFormat:
    """Tests for --format output flag."""

    def _patch_pack(self, monkeypatch):
        mock_pack = MagicMock()
        mock_pack.to_dict.return_value = {
            "schema_version": "1.0",
            "overall_verdict": "yellow",
            "verdict": "yellow",
            "summary": "Test",
            "checks": [
                {
                    "check_id": "FakeChecker",
                    "verdict": "yellow",
                    "reason": "ko_phrase_found",
                    "evidence": [{"doc_id": "doc.pdf", "page": 1, "snippet": "test"}],
                }
            ],
        }

        import kosniper.cli
        monkeypatch.setattr(kosniper.cli, "make_evidence_pack", lambda *_, **__: mock_pack)

    def test_json_format_compact_single_line(self, monkeypatch, capsys):
        self._patch_pack(monkeypatch)

        from kosniper.cli import main

        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test", "--format", "json"])
        captured = capsys.readouterr()

        assert result == 0
        assert "\n" not in captured.out.strip()
        assert captured.out.startswith("{")

    def test_pretty_format_multiline(self, monkeypatch, capsys):
        self._patch_pack(monkeypatch)

        from kosniper.cli import main

        result = main(["--doc-id", "test.pdf", "--page", "1", "--text", "test", "--format", "pretty"])
        captured = capsys.readouterr()

        assert result == 0
        assert "\n" in captured.out.strip()

    def test_invalid_format_exits_with_code_2(self, monkeypatch):
        self._patch_pack(monkeypatch)

        from kosniper.cli import main

        with pytest.raises(SystemExit) as excinfo:
            main(["--doc-id", "test.pdf", "--page", "1", "--text", "test", "--format", "xml"])
        assert excinfo.value.code == 2
