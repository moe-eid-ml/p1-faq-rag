"""Checker registry for KOSniper pipeline.

Order matters: checkers run in list order, results aggregated by precedence.
To add a checker: append its class to the tuple in get_checker_classes().
"""
from typing import Tuple, Type

from kosniper.checkers.base import Checker


def get_checker_classes() -> Tuple[Type[Checker], ...]:
    """Return registered checker classes in deterministic order.

    Returns a tuple (immutable) to prevent accidental mutation.
    Lazy imports inside function to avoid circular dependencies.
    """
    from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker
    from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker

    return (
        MinimalKoPhraseChecker,
        TurnoverThresholdChecker,
    )
