import logging
import confuse
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
from ob.data_colection.base_components.address_dispatcher import AddressedProtocol
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.ob_config import SingletonConfig

logger = logging.getLogger(__name__.rsplit('.')[-1])


class TreeComponent(ABC):
    """
    This is a base class component in tree.

    :ivar _component_name: this is name of tree component, used for debug

    :param component_name: this is name of tree component, used for debug

    Conforms to:
        ProvidesResponseProtocol
    """
    COMPONENT_DEFAULT_NAME: str = 'TreeComponent'

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

    def _get_cfg(self, name_cfg: str, default=None, use_default_settings=True):
        """
        The method looks for a value in the configuration file and returns it.

        :param name_cfg: name of config value
        :param default: default value if key not exist in config
        :param use_default_settings: use default settings if default value is None and can not get settings
        :return: config value or None if method can't find it
        """
        try:
            value = SingletonConfig.get_config()['tree'][self._component_name][name_cfg].get()  # local
        except confuse.exceptions.NotFoundError:
            if use_default_settings:
                try:
                    value = SingletonConfig.get_config()['data_collection'][self.COMPONENT_DEFAULT_NAME][
                        name_cfg].get()  # global
                except confuse.exceptions.NotFoundError:
                    value = default  # default
            else:
                value = default
        return value


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
class AddressedResponderProtocol(ProvidesResponseProtocol, AddressedProtocol, Protocol):
    pass
