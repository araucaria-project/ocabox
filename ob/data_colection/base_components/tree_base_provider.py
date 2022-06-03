import logging
from abc import ABC
from ob.data_colection.base_components.tree_component import TreeComponent, ProvidesResponseProtocol
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value import Value
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
        This is the main method to generate the Value that is returned in response

        :param request: ValueRequest
        :return: Value
        """
        raise NotImplementedError  # TODO: exception: HasNotValue zamiast tego

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
            return ValueResponse(request.address, v, True)
        except NotImplementedError:
            logger.warning(f"Method get_value() is not implemented")

        if self._subcontractor:
            return self._subcontractor.get_response(request)
        else:
            # This provider doesn't provide response and there is no next provider
            re = ResponseError(3001, '', repr(self), 'CRITICAL')
            logger.info(f'Provider try call subcontractor but he does not exist')
            return ValueResponse(request.address, None, False, re)
