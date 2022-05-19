from abc import ABC, abstractmethod
from typing import List


class RequestSolverInterface(ABC):

    @abstractmethod
    async def get_answer(self, request: List[dict]) -> List[dict]:
        pass
