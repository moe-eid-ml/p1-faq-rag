from abc import ABC, abstractmethod
from typing import Optional

from kosniper.contracts import CheckerResult


class Checker(ABC):
    name: str

    @abstractmethod
    def run(self, text: str, doc_id: str, page_number: int) -> Optional[CheckerResult]:
        raise NotImplementedError
