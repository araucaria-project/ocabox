from abc import ABC, abstractmethod
from typing import List

from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol


class BaseRequestSolver(ABC):

    def __init__(self, data_provider: ProvidesResponseProtocol, **kwargs):
        self.data_provider: ProvidesResponseProtocol = data_provider

    @abstractmethod
    async def get_answer(self, request: List[dict]) -> List[dict]:
        """
        This method is designed to provide a response to given request by calling to data_provider. The received query
        is a list of minor queries for single values. This method runs a separate task for each query in order to
        reduce the waiting time. Created tasks are associated with this method and if the task that called this method
        is canceled, all tasks created by it will also be canceled.

        :param request: List of dictionaries representing ValueRequest
        :return: List of dictionaries representing ValueResponse
        """
        pass

    async def get_single_answer(self, request: dict) -> dict:
        """
        The method reads the query details and calls the provider for an answer for a single query.

        :param request: dictionary representing ValueRequest
        :return: dictionary representing ValueResponse
        """
        pass

    async def run_tree(self):
        """
        This method starts cascading asynchronous tree initialization.

        :return:
        """
        await self.data_provider.run()

    async def stop_tree(self):
        """
        This method stops cascading asynchronous tree elements.

        :return:
        """
        await self.data_provider.stop()
