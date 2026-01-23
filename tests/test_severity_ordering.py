"""MC-KOS-44: Severity-aware ordering tests.

Tests: 6 including 1 adversarial per Sniper process rules.
"""

from kosniper.evidence.select import apply_evidence_policy, severity_rank


class TestSeverityRank:
    """Tests for severity_rank helper."""

    def test_severity_rank_ordering(self):
        """Verify severity order: red < yellow < abstain < green (lower = worse)."""
        assert severity_rank("red") < severity_rank("yellow")
        assert severity_rank("yellow") < severity_rank("abstain")
        assert severity_rank("abstain") < severity_rank("green")

    def test_severity_rank_case_insensitive(self):
        """Verify case insensitivity."""
        assert severity_rank("RED") == severity_rank("red")
        assert severity_rank("Yellow") == severity_rank("yellow")

    def test_severity_rank_unknown_sorts_last(self):
        """Unknown verdicts sort after green (robustness)."""
        assert severity_rank("unknown") > severity_rank("green")
        assert severity_rank("") > severity_rank("green")


class TestSeverityOrdering:
    """Tests for severity-aware check ordering."""

    def test_checks_ordered_worst_first(self):
        """Golden: mixed-verdict checks are ordered RED → YELLOW → GREEN."""
        checks = [
            {"check_id": "CheckerA", "verdict": "green", "evidence": []},
            {"check_id": "CheckerB", "verdict": "yellow", "evidence": []},
            {"check_id": "CheckerC", "verdict": "red", "evidence": []},
        ]

        result = apply_evidence_policy(checks)

        # RED should be first, YELLOW second, GREEN third
        assert result[0]["verdict"] == "red"
        assert result[0]["check_id"] == "CheckerC"
        assert result[1]["verdict"] == "yellow"
        assert result[1]["check_id"] == "CheckerB"
        assert result[2]["verdict"] == "green"
        assert result[2]["check_id"] == "CheckerA"

    def test_same_severity_preserves_original_order(self):
        """Stable tiebreaker: same severity maintains original order."""
        checks = [
            {"check_id": "First", "verdict": "yellow", "evidence": []},
            {"check_id": "Second", "verdict": "yellow", "evidence": []},
            {"check_id": "Third", "verdict": "yellow", "evidence": []},
        ]

        result = apply_evidence_policy(checks)

        # Original order preserved for same severity
        assert result[0]["check_id"] == "First"
        assert result[1]["check_id"] == "Second"
        assert result[2]["check_id"] == "Third"

    def test_adversarial_red_never_buried_after_yellow(self):
        """ADVERSARIAL: RED check must never appear after YELLOW (prevents buried findings)."""
        # Scenario: checkers produce YELLOW first, then RED later
        # This simulates a realistic case where a later checker finds a hard KO
        checks = [
            {"check_id": "EarlyChecker", "verdict": "yellow", "evidence": [
                {"doc_id": "test.pdf", "page": 1, "snippet": "minor issue"}
            ]},
            {"check_id": "TurnoverChecker", "verdict": "green", "evidence": []},
            {"check_id": "LateKOChecker", "verdict": "red", "evidence": [
                {"doc_id": "test.pdf", "page": 5, "snippet": "Ausschlusskriterium"}
            ]},
            {"check_id": "AnotherYellow", "verdict": "yellow", "evidence": [
                {"doc_id": "test.pdf", "page": 3, "snippet": "another warning"}
            ]},
        ]

        result = apply_evidence_policy(checks)

        # Find positions
        red_pos = next(i for i, c in enumerate(result) if c["verdict"] == "red")
        yellow_positions = [i for i, c in enumerate(result) if c["verdict"] == "yellow"]
        green_pos = next(i for i, c in enumerate(result) if c["verdict"] == "green")

        # RED must be first (position 0)
        assert red_pos == 0, f"RED buried at position {red_pos}, expected 0"

        # All YELLOW must come after RED but before GREEN
        for yp in yellow_positions:
            assert yp > red_pos, f"YELLOW at {yp} before RED at {red_pos}"
            assert yp < green_pos, f"YELLOW at {yp} after GREEN at {green_pos}"

        # Verify the specific ordering
        verdicts = [c["verdict"] for c in result]
        assert verdicts == ["red", "yellow", "yellow", "green"]
