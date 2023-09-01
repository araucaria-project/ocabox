import logging
import confuse
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, List, Tuple
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
    _SUFFIX = "_RESOURCE"

    def __init__(self, component_name: str, **kwargs):
        super().__init__(**kwargs)
        self._component_name: str = component_name  # this is name of tree component, used for debug and errors
        self._resource_name = self._component_name + self._SUFFIX
        self.target_requests = None
        self.tree_path = None

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

    def get_type(self):
        return type(self).__name__

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

    @abstractmethod
    def get_configuration(self) -> dict:
        """
        Method returns self configuration and children configurations as dict.

        :return: dictionary witch configuration
        """
        raise NotImplementedError

    def _get_self_configuration(self) -> dict:
        out = {self.get_name(): {"child": {},
                                 "type": self.get_type(),
                                 "config": self._extract_cfg(
                                     SingletonConfig.get_config()['data_collection'][self.COMPONENT_DEFAULT_NAME])}}
        out.get(self.get_name()).get("config").update(self._extract_cfg(SingletonConfig.get_config()['tree'][self._component_name]))
        return out

    def _extract_cfg(self, x):
        out = {}
        items = x.items()
        for k, i in items:
            if isinstance(i.get(), dict):
                out[k] = self._extract_cfg(i)
            else:
                out[k] = i.get()
        return out

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

    def get_resources(self) -> List[Tuple[str, List[str]]]:
        """
        The method returns the resources of this component

        :return: list of resources witch address
        """
        raise NotImplementedError

    def get_resource_name(self) -> str:
        return self._resource_name


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

    def get_resources(self) -> List[Tuple[str, List[str]]]:
        pass

    def get_name(self):
        pass

    def get_configuration(self):
        pass


@runtime_checkable
class AddressedResponderProtocol(ProvidesResponseProtocol, AddressedProtocol, Protocol):
    pass
