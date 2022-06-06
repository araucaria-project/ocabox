import copy
import logging
from abc import ABC, abstractmethod
from ob.data_colection.base_components.address_dispatcher import AddressDispatcher
from ob.data_colection.coded_error import AddressError
from ob.data_colection.value import Value

from ob.data_colection.value_call import ValueRequest, ValueResponse


logger = logging.getLogger(__name__)


class ValueSet(AddressDispatcher):

    def __init__(self, source, source_name: str, subcontractor: AddressDispatcher = None):
        super().__init__(source_name)
        self.source = source
        self.subcontractor: AddressDispatcher = subcontractor

    @abstractmethod
    def get_value(self, request: ValueRequest) -> Value or None:
        """
        This is the main method to generate the Value that is returned as response
        :param request: ValueRequest
        :return: Value
        """
        pass

    @abstractmethod
    def get_source(self):
        pass

    @abstractmethod
    def set_source(self, source):
        pass

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
        try:
            v = self.get_value(request)
        except AddressError as e:
            # get response from next provider in tree if address is incorrect then broker should solve this
            if self.subcontractor:
                request.index += 1
                return self.subcontractor.get_response(request)
            else:
                return ValueResponse(request.address, None)


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
            # raise AddressError(request.address, message=f'Can not find target for address <{str(request.address)}>.')
