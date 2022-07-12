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
    async def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.

        :param request: ValueRequest
        :raise NotImplementedError: always because it is abstract method
        :return: ValueResponse
        """
        raise NotImplementedError

    def __repr__(self):
        return self._component_name

    def get_name(self):
        return self._component_name

    @abstractmethod
    async def run(self):
        """
        This method runs all the necessary tasks in the async loop of this component and the children components.

        :return:
        """
        raise NotImplementedError

    @abstractmethod
    async def stop(self):
        """
        This method closes all the tasks of this component and the children components running in the asynchronous loop.

        :return:
        """
        raise NotImplementedError


@runtime_checkable
class ProvidesResponseProtocol(Protocol):
    _component_name: str

    async def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.

        :param request: ValueRequest
        :return: ValueResponse
        """
        pass

    async def run(self):
        """
        This method runs all the necessary tasks in the async loop of this component and the children components.

        :return:
        """
        pass

    async def stop(self):
        """
        This method closes all the tasks of this component and the children components running in the asynchronous loop.

        :return:
        """
        pass

@runtime_checkable
class AddressedResponderProtocol (ProvidesResponseProtocol, AddressedProtocol, Protocol):
    pass
