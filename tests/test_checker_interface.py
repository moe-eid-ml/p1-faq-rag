"""Interface guard: checkers must align with base signature."""

import inspect
from typing import Optional, get_args, get_origin

from kosniper.checkers.base import Checker
from kosniper.checkers.registry import get_checker_classes


def _is_optional_str(annotation) -> bool:
    """Accept Optional[str] or PEP604 str | None annotations."""
    if annotation is Optional[str]:
        return True
    origin = get_origin(annotation)
    if origin is None:
        return False
    args = set(get_args(annotation))
    return str in args and type(None) in args


def test_checker_run_signature_matches_base():
    base_sig = inspect.signature(Checker.run)
    base_params = list(base_sig.parameters.values())
    assert _is_optional_str(base_params[1].annotation), "Base Checker.run must accept Optional[str]"
    assert base_params[2].annotation is str, "Base Checker.run must annotate doc_id as str"
    assert base_params[3].annotation is int, "Base Checker.run must annotate page_number as int"

    checker_classes = list(get_checker_classes())
    assert checker_classes, "No registered checkers found to validate"

    for cls in checker_classes:
        sig = inspect.signature(cls.run)
        params = list(sig.parameters.values())
        # First four params should match names and order: self, text, doc_id, page_number
        assert [p.name for p in params[:4]] == [p.name for p in base_params[:4]], cls.__name__
        # Keep the base contract: doc_id is str, page_number is int
        assert params[2].annotation is str, f"{cls.__name__}.run must annotate doc_id as str"
        assert params[3].annotation is int, f"{cls.__name__}.run must annotate page_number as int"
        assert _is_optional_str(params[1].annotation), f"{cls.__name__}.run must accept Optional[str] for text"
        # Ensure **kwargs present to prevent signature drift
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params), cls.__name__
