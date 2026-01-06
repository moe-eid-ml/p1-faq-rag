from abc import ABC, abstractmethod
from kosniper.contracts import CheckerResult

class Checker(ABC):
    name: str

    @abstractmethod
    def run(self, text: str, doc_id: str, page_number: int) -> CheckerResult:
        raise NotImplementedError
