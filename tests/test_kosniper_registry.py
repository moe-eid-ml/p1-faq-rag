"""MC-KOS-07: Registry determinism and integration tests."""

from kosniper.checkers.registry import get_checker_classes
from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker
from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker
from kosniper.pipeline import run_single_page
from kosniper.contracts import TrafficLight


class TestRegistryDeterminism:
    """Verify registry returns consistent, deterministic results."""

    def test_get_checker_classes_returns_tuple(self):
        """Registry returns immutable tuple, not list."""
        result = get_checker_classes()
        assert isinstance(result, tuple)

    def test_get_checker_classes_deterministic_order(self):
        """Multiple calls return same order."""
        first = get_checker_classes()
        second = get_checker_classes()
        third = get_checker_classes()
        assert first == second == third

    def test_registry_order_matches_expected(self):
        """Explicit order assertion to catch accidental reordering."""
        expected = (MinimalKoPhraseChecker, TurnoverThresholdChecker)
        assert get_checker_classes() == expected

    def test_no_duplicate_checkers_in_registry(self):
        """Registry must not contain duplicate checker classes."""
        classes = get_checker_classes()
        assert len(classes) == len(set(classes)), "Duplicate checker in registry"


class TestPipelineIntegration:
    """Verify pipeline uses registry correctly."""

    def test_pipeline_runs_all_registered_checkers(self):
        """Pipeline runs every checker from registry that produces findings."""
        # Text that triggers both checkers
        text = "Ausschlusskriterium: Mindestumsatz 500.000 EUR"
        result = run_single_page(text, "doc.pdf", 1, {"annual_turnover_eur": 400_000})

        # Both checkers should produce findings for this text
        checker_names = {r.checker_name for r in result.results}
        assert "MinimalKoPhraseChecker" in checker_names
        assert "TurnoverThresholdChecker" in checker_names

    def test_pipeline_respects_registry_order(self):
        """Results appear in registry order when both checkers produce findings."""
        text = "Ausschlusskriterium: Mindestumsatz 500.000 EUR"
        result = run_single_page(text, "doc.pdf", 1, {"annual_turnover_eur": 400_000})

        # Verify results are in registry order
        registry_order = [cls.name for cls in get_checker_classes()]
        result_order = [r.checker_name for r in result.results]

        # Results should be a subsequence of registry order
        registry_idx = 0
        for name in result_order:
            while registry_idx < len(registry_order) and registry_order[registry_idx] != name:
                registry_idx += 1
            assert registry_idx < len(registry_order), f"{name} not in expected order"
            registry_idx += 1

    def test_pipeline_aggregation_unchanged(self):
        """Verify aggregation behavior preserved after registry refactor."""
        # RED from turnover takes precedence
        text = "Ausschlusskriterium: Mindestumsatz 500.000 EUR"
        result = run_single_page(text, "doc.pdf", 1, {"annual_turnover_eur": 400_000})
        assert result.overall == TrafficLight.RED

        # YELLOW when turnover met but phrase found
        result2 = run_single_page(text, "doc.pdf", 1, {"annual_turnover_eur": 600_000})
        assert result2.overall == TrafficLight.YELLOW

        # GREEN when no findings
        result3 = run_single_page("Bitte reichen Sie Ihre Unterlagen ein.", "doc.pdf", 1)
        assert result3.overall == TrafficLight.GREEN
