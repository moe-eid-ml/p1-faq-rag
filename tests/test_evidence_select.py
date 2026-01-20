"""MC-KOS-35: Evidence selection policy tests (minimal suite).

Tests for evidence sorting, deduplication, limits, and validation.
Tests: 3 including 1 adversarial per Sniper process rules.
"""

from kosniper.evidence.select import apply_evidence_policy, validate_evidence_offset_basis


class TestEvidenceSelect:
    """Evidence selection policy test suite."""

    def test_sorting_and_dedupe_deterministic(self):
        """Sorting and deduplication produce deterministic output."""
        # Create evidence in random order with duplicates
        evidence1 = [
            {"doc_id": "b.pdf", "page": 2, "start_offset": 10, "end_offset": 20,
             "snippet": "second", "offset_basis": "normalized_text_v1"},
            {"doc_id": "a.pdf", "page": 1, "start_offset": 5, "end_offset": 15,
             "snippet": "first", "offset_basis": "normalized_text_v1"},
            {"doc_id": "a.pdf", "page": 1, "start_offset": 5, "end_offset": 15,
             "snippet": "first", "offset_basis": "normalized_text_v1"},  # duplicate
            {"doc_id": "a.pdf", "page": 1, "snippet": "no offsets"},  # missing offsets
        ]

        # Shuffled order
        evidence2 = [
            {"doc_id": "a.pdf", "page": 1, "snippet": "no offsets"},
            {"doc_id": "a.pdf", "page": 1, "start_offset": 5, "end_offset": 15,
             "snippet": "first", "offset_basis": "normalized_text_v1"},
            {"doc_id": "b.pdf", "page": 2, "start_offset": 10, "end_offset": 20,
             "snippet": "second", "offset_basis": "normalized_text_v1"},
            {"doc_id": "a.pdf", "page": 1, "start_offset": 5, "end_offset": 15,
             "snippet": "first", "offset_basis": "normalized_text_v1"},
        ]

        checks1 = [{"check_id": "test", "verdict": "red", "evidence": evidence1}]
        checks2 = [{"check_id": "test", "verdict": "red", "evidence": evidence2}]

        result1 = apply_evidence_policy(checks1)
        result2 = apply_evidence_policy(checks2)

        # Same output regardless of input order
        assert result1[0]["evidence"] == result2[0]["evidence"]

        # Duplicates removed (4 -> 3)
        assert len(result1[0]["evidence"]) == 3

        # Sorted: a.pdf comes before b.pdf, offsets before no-offsets
        ev = result1[0]["evidence"]
        assert ev[0]["doc_id"] == "a.pdf"
        assert ev[0]["snippet"] == "first"
        assert ev[1]["doc_id"] == "a.pdf"
        assert ev[1]["snippet"] == "no offsets"  # no offsets sorts last
        assert ev[2]["doc_id"] == "b.pdf"

    def test_limits_enforced(self):
        """max_k, max_total, and snippet truncation are enforced."""
        # Create many evidence items with long snippets
        long_snippet = "A" * 300
        evidence = [
            {"doc_id": "a.pdf", "page": i, "snippet": long_snippet}
            for i in range(10)
        ]

        checks = [
            {"check_id": "check1", "verdict": "red", "evidence": evidence[:5]},
            {"check_id": "check2", "verdict": "red", "evidence": evidence[5:]},
        ]

        result = apply_evidence_policy(checks, max_k=3, max_total=5, max_snippet_len=50)

        # max_k=3 per check
        assert len(result[0]["evidence"]) == 3

        # max_total=5 overall (3 from first, 2 from second)
        assert len(result[1]["evidence"]) == 2
        total = sum(len(c["evidence"]) for c in result)
        assert total == 5

        # Snippets truncated to max_snippet_len with "..."
        for check in result:
            for ev in check["evidence"]:
                assert len(ev["snippet"]) == 50
                assert ev["snippet"].endswith("...")

    def test_adversarial_offset_basis_fails_closed(self):
        """ADVERSARIAL: Missing offset_basis with offsets still fails closed."""
        # Evidence with offsets but missing offset_basis
        checks = [{
            "check_id": "test",
            "verdict": "red",
            "evidence": [{
                "doc_id": "test.pdf",
                "page": 1,
                "start_offset": 0,
                "end_offset": 10,
                "snippet": "test",
                # offset_basis intentionally missing
            }],
        }]

        error = validate_evidence_offset_basis(checks)
        assert error is not None
        assert "offset_basis" in error

        # Wrong offset_basis also fails
        checks[0]["evidence"][0]["offset_basis"] = "raw_text"
        error = validate_evidence_offset_basis(checks)
        assert error is not None
        assert "normalized_text_v1" in error

        # Correct offset_basis passes
        checks[0]["evidence"][0]["offset_basis"] = "normalized_text_v1"
        error = validate_evidence_offset_basis(checks)
        assert error is None
