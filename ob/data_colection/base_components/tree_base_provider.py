import logging
from abc import ABC

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_component import TreeComponent, ProvidesResponseProtocol
from ob.data_colection.coded_error import OBStructureError
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value import Value, OBValueError
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class TreeBaseProvider(TreeComponent, ABC):
    """
    P0

    :param component_name: this is name of tree component, used for debug
    :param subcontractor: instance of next component in tree

    :ivar _subcontractor: instance of next component in tree

    Conforms to:
        ProvidesResponseProtocol
    """

    def __init__(self, component_name: str, subcontractor: ProvidesResponseProtocol = None, **kwargs):
        super().__init__(component_name=component_name, **kwargs)
        self._subcontractor: ProvidesResponseProtocol = subcontractor

    def get_value(self, request: ValueRequest) -> Value or None:
        """
        This is the main method of generating a return value from a response.
        A method can raise an OBStructureError error if the address is not directed to that component but to components
        deeper in the tree. The method can also raise OBValueError, AddressError errors if you encounter any problems
        generating the response. The errors may contain the appropriate error codes. This will send an error response
        to the client.

        :param request: ValueRequest
        :raise OBStructureError: when method can't provide value and algorythm should looking a value in sub provider
        :raise OBValueError: when the value cannot be generated and an error response should be returned to the client
        :raise AddressError: when address is wrong or damaged
        :return: Value
        """
        raise OBStructureError

    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This is the main method that will be called to get a response to a given request. It requires a defined
        get_value() method to work properly. If there are any problems reading the address, an empty response will be
        returned.

        :param request: ValueRequest
        :return: ValueResponse
        """
        try:
            v = self.get_value(request)
            if isinstance(v, Value) or v is None:
                return ValueResponse(request.address, v, True)
            logger.error(f'Method get_value() returned wrong type, expected Value or None')
            re = ResponseError(2002, 'Can not create value', repr(self))
            return ValueResponse(request.address, None, False, re)
        except OBStructureError:
            if self._subcontractor:
                try:
                    return self._subcontractor.get_response(request)
                except AttributeError:
                    re = ResponseError(3002, '', repr(self), 'CRITICAL')
                    logger.warning(f"Provider try call subcontractor but he doesn't has method get_response()")
                    return ValueResponse(request.address, None, False, re)
            else:
                # This provider doesn't provide response and there is no next provider
                re = ResponseError(3001, '', repr(self), 'CRITICAL')
                logger.info(f'Provider try call subcontractor but he does not exist')
                return ValueResponse(request.address, None, False, re)
        except OBValueError as e:
            re = ResponseError(e.code, e.message, repr(self))
            return ValueResponse(request.address, None, False, re)
        except AddressError as e:
            re = ResponseError(e.code, e.message, repr(self))
            return ValueResponse(request.address, None, False, re)
