import logging
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from ob.data_colection.base_components.address_dispatcher import AddressedProtocol
from ob.data_colection.value_call import ValueRequest, ValueResponse


logger = logging.getLogger(__name__)


class TreeComponent(ABC):
    """
    This is a base class component in tree.

    :ivar _component_name: this is name of tree component, used for debug

    :param component_name: this is name of tree component, used for debug

    Conforms to:
        ProvidesResponseProtocol
    """
    def __init__(self, component_name: str, **kwargs):
        super().__init__(**kwargs)
        self._component_name: str = component_name  # this is name of tree component, used for debug and errors

    @abstractmethod
    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.

        :param request: ValueRequest
        :raise NotImplementedError: always because it is abstract method
        :return: ValueResponse
        """
        raise NotImplementedError

    def __repr__(self):
        return self._component_name


@runtime_checkable
class ProvidesResponseProtocol(Protocol):
    _component_name: str

    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.

        :param request: ValueRequest
        :return: ValueResponse
        """
        pass


@runtime_checkable
class AddressedResponderProtocol (ProvidesResponseProtocol, AddressedProtocol, Protocol):
    pass

