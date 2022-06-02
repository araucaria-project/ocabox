import logging
from abc import ABC, abstractmethod
from typing import Protocol

from ob.data_colection.value_call import ValueRequest, ValueResponse


logger = logging.getLogger(__name__)


class ProvidesResponseProtocol(Protocol):
    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.
        :param request: ValueRequest
        :return: ValueResponse
        """
        pass


class TreeComponent(ABC):
    """
    This is a base class component in tree.

    Attributes:
        component_name (str): this is name of tree component, used for debug

    Conforms to:
        ProvidesResponseProtocol
    """
    def __init__(self, component_name: str, **kwargs):
        super().__init__(**kwargs)
        self._component_name: str = component_name  # this is name of tree component, used for debug

    @abstractmethod
    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.
        :param request: ValueRequest
        :return: ValueResponse
        """
        raise NotImplementedError

    def __repr__(self):
        return self._component_name
