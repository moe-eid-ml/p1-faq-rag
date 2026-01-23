"""MC-KOS-45: Configurable scan limits tests.

Tests: 3 including 1 adversarial per Sniper process rules.
"""

import json
import subprocess
import sys
from pathlib import Path

from kosniper.cli import _resolve_limit, DEFAULT_MAX_PDF_BYTES, DEFAULT_MAX_SCAN_PAGES

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestResolveLimitHelper:
    """Tests for _resolve_limit helper function."""

    def test_default_values_unchanged(self):
        """Defaults: 50MB and 500 pages when no CLI/env override."""
        # No CLI value, no env var → use default
        assert _resolve_limit(None, "NONEXISTENT_VAR", DEFAULT_MAX_PDF_BYTES) == 50_000_000
        assert _resolve_limit(None, "NONEXISTENT_VAR", DEFAULT_MAX_SCAN_PAGES) == 500

    def test_cli_value_takes_precedence(self):
        """CLI value overrides env and default."""
        # CLI value should win
        assert _resolve_limit(10_000_000, "NONEXISTENT_VAR", DEFAULT_MAX_PDF_BYTES) == 10_000_000
        assert _resolve_limit(100, "NONEXISTENT_VAR", DEFAULT_MAX_SCAN_PAGES) == 100

    def test_env_var_overrides_default(self, monkeypatch):
        """Env var overrides default when CLI not set."""
        monkeypatch.setenv("TEST_LIMIT_VAR", "25000000")
        assert _resolve_limit(None, "TEST_LIMIT_VAR", DEFAULT_MAX_PDF_BYTES) == 25_000_000


class TestConfigurableLimitsCLI:
    """Tests for configurable limits via CLI."""

    def test_override_via_cli_flag(self):
        """--max-scan-pages flag limits page processing."""
        pdf_path = FIXTURES_DIR / "fixture_ko_page2.pdf"

        # With default (500), 2-page fixture should scan normally
        result_default = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--pdf", str(pdf_path), "--scan", "--format", "json"],
            capture_output=True,
            text=True,
        )
        assert result_default.returncode == 0
        output_default = json.loads(result_default.stdout)
        # Should have scanned pages (verdict red from KO phrase)
        assert output_default["overall_verdict"] == "red"

        # With --max-scan-pages=1, 2-page fixture exceeds limit → YELLOW abort
        result_limited = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--pdf", str(pdf_path), "--scan",
             "--max-scan-pages", "1", "--format", "json"],
            capture_output=True,
            text=True,
        )
        assert result_limited.returncode == 0
        output_limited = json.loads(result_limited.stdout)
        assert output_limited["overall_verdict"] == "yellow"
        assert any(
            "SCAN_ABORTED" in (ev.get("snippet") or "")
            for c in output_limited.get("checks", [])
            for ev in c.get("evidence", [])
        )

    def test_adversarial_tiny_limit_triggers_abort_with_evidence(self, monkeypatch):
        """ADVERSARIAL: Tiny limit via env var triggers abort with SCAN_ABORTED + YELLOW."""
        pdf_path = FIXTURES_DIR / "fixture_ko_page2.pdf"

        # Set tiny page limit via env var
        monkeypatch.setenv("KOSNIPER_MAX_SCAN_PAGES", "0")

        result = subprocess.run(
            [sys.executable, "-m", "kosniper.cli", "--pdf", str(pdf_path), "--scan", "--format", "json"],
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "KOSNIPER_MAX_SCAN_PAGES": "0"},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Must be YELLOW (fail-closed, not GREEN)
        assert output["overall_verdict"] == "yellow", "Fail-closed: limit exceeded must be YELLOW"
        assert output["overall_verdict"] != "green", "Never false-green on limit exceeded"

        # Must have ScanLimitGuard check with SCAN_ABORTED evidence
        checks = output.get("checks", [])
        assert len(checks) >= 1, "Must have at least one check (ScanLimitGuard)"

        limit_check = next((c for c in checks if c.get("check_id") == "ScanLimitGuard"), None)
        assert limit_check is not None, "ScanLimitGuard check must be present"
        assert limit_check["verdict"] == "yellow"
        assert limit_check["reason"] == "scan_limit_exceeded"

        evidence = limit_check.get("evidence", [])
        assert len(evidence) >= 1, "ScanLimitGuard must have evidence"
        assert "SCAN_ABORTED" in evidence[0].get("snippet", ""), "Evidence must contain SCAN_ABORTED"
        assert "exceeds max_pages=0" in evidence[0].get("snippet", ""), "Evidence must show the limit"
