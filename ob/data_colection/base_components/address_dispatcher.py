import logging
from abc import ABC
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class AddressDispatcher(ABC):
    """
    This class represents one component in the tree. All components except first must have a name.
    First component is initial so his name are not included in address

    :ivar _source_name: This is a component name with will be used to decode address

    :param source_name: This is a component name with will be used to decode address

    Conforms:
        AddressedProtocol
    """
    def __init__(self, source_name: str, **kwargs):
        super().__init__(**kwargs)
        self._source_name: str = 'Default'  # this is to remember that there is such a variable
        self._set_source_name(source_name)  # here variable self._source_name is changed

    def _set_source_name(self, source_name: str):
        """
        This method sets the name of this class to use when decoding the query address

        :param source_name: name for that class
        :raise ValueError: if source_name has wrong format or is None
        :return: None
        """
        if not source_name:
            logger.warning(f"Name of the component is None, so will be set to default name.")
            source_name = self._source_name
        if self._source_name == source_name:
            logger.warning(f"Name of the component is default, make sure you haven't forgotten to add name.")
        if not source_name or type(source_name) != str:
            raise ValueError
        self._source_name = source_name

    def get_source_name(self) -> str:
        """
        This method return name of this class to use when decoding the query address.

        :return: name of that component with will be used to decode address
        """
        return self._source_name


@runtime_checkable  # this is need only for pycharm check correct code
class AddressedProtocol(Protocol):
    def get_source_name(self) -> str:
        """
        This method return name of this class to use when decoding the query address.

        :return: name of that component with will be used to decode address
        """
        pass

