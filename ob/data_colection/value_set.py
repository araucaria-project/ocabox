import copy
import logging
from abc import ABC, abstractmethod
from ob.data_colection.address import AddressError
from ob.data_colection.value import Value

from ob.data_colection.value_call import ValueRequest, ValueResponse
import typing

if typing.TYPE_CHECKING:    # TODO CZY TAKI ZABIEG JKEST OK, to chroni przed importem cyklicznym MIKOŁAJ
    from ob.data_colection.value_broker import ValueBroker


logger = logging.getLogger(__name__)


class ValueSet(ABC):

    def __init__(self, source, source_address: str, subcontractor: 'ValueBroker' = None):
        self.source = source
        self._source_address: str = 'Default'  # this is to remember that there is such a variable
        self._set_source_address(source_address)  # here variable self._source_address is changed
        self.subcontractor: 'ValueBroker' = subcontractor

    @abstractmethod
    def get_value(self, request: ValueRequest) -> Value or None:
        """
        This is the main method to generate the Value that is returned as response.
        :param request: ValueRequest
        :return: Value
        """
        pass

    @abstractmethod
    def get_source(self):
        pass

    def get_source_address(self):
        """
        This method return name of this class to use when decoding the query address.
        :return: name of that class
        """
        return self._source_address

    @abstractmethod
    def set_source(self, source):
        pass

    def _set_source_address(self, source_address):
        """
        This method sets the name of this class to use when decoding the query address.
        :param source_address: name for that class
        :return:
        """
        if not source_address:
            raise ValueError
        self._source_address = source_address

    @staticmethod
    def _is_last_target(request: ValueRequest):
        """
        The method checks if the current class is the last target of the query.
        If address is to short raise AddressError
        :param request: ValueRequest
        :return: True if the query response must be taken from this class.
        """
        if len(request.address) - request.index == 1:
            return True
        if len(request.address) - request.index < 1:
            raise AddressError(request.address, message=f'Address <{str(request.address)}> is to short.')
        return False

    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This is the main method that will be called to get a response to a given request. It requires a defined
        get_value() method to work properly. If there are any problems reading the address, an empty response will be
        returned.
        If address is incorrect raise AddressError
        :param request: ValueRequest
        :return: ValueResponse
        """
        # get value from here
        if self._is_last_target(request):  # Here can raise AddressError
            address = copy.copy(request.address)  # copy address because the request is forwarded and can be edited
            v = self.get_value(request)
            if v:
                return ValueResponse(address, v)
            return ValueResponse(address, None)
        # get response from next provider in tree if address is incorrect then broker should solve this
        if self.subcontractor:
            return self.subcontractor.get_response(request)
        else:
            return ValueResponse(request.address, None)
            # TODO Don't known provider, return empty response or raise
            #  error and don't ansvear MIKOŁAJ
            # raise AddressError(request.address, message=f'Can not find target for address <{str(request.address)}>.')
