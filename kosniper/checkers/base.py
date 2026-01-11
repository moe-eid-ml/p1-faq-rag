from abc import ABC, abstractmethod
from typing import Any, Optional

from kosniper.contracts import CheckerResult


class Checker(ABC):
    name: str

    @abstractmethod
    def run(
        self, text: Optional[str], doc_id: str, page_number: int, **kwargs: Any
    ) -> Optional[CheckerResult]:
        raise NotImplementedError
