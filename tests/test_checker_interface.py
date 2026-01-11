"""Interface guard: checkers must align with base signature."""

import inspect
from typing import Optional

from kosniper.checkers.base import Checker
from kosniper.checkers.registry import get_checker_classes


def test_checker_run_signature_matches_base():
    base_sig = inspect.signature(Checker.run)
    base_params = list(base_sig.parameters.values())

    for cls in get_checker_classes():
        sig = inspect.signature(cls.run)
        params = list(sig.parameters.values())
        # First three params should match names and order: self, text, doc_id, page_number
        assert [p.name for p in params[:3]] == [p.name for p in base_params[:3]], cls.__name__
        assert params[1].annotation in (Optional[str], str, base_params[1].annotation)
        # Ensure **kwargs present to prevent signature drift
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params), cls.__name__
