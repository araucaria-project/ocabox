from abc import ABC, abstractmethod
from typing import List

from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol


class BaseRequestSolver(ABC):

    def __init__(self, data_provider: ProvidesResponseProtocol, **kwargs):
        self.data_provider: ProvidesResponseProtocol = data_provider

    @abstractmethod
    async def get_answer(self, request: List[dict]) -> List[dict]:
        """
        The method reads the details of the query and calls the provider for an answer.

        :param request: List of dictionaries representing ValueRequest
        :return: List of dictionaries representing ValueResponse
        """
        pass
