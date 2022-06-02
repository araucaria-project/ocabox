import logging
from typing import List

from ob.data_colection.base_components.address_dispatcher import AddressDispatcher
from ob.data_colection.base_components.tree_base_broker import TreeBaseBroker
from ob.data_colection.base_components.tree_component import TreeComponent
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class TreeBroker(TreeBaseBroker, AddressDispatcher):
    """
    BX
    """

    def __init__(self, component_name: str, source_name: str, list_providers: List[TreeComponent] = None, **kwargs):
        super().__init__(component_name=component_name, list_providers=list_providers, source_name=source_name,
                         **kwargs)

    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.
        :param request: ValueRequest
        :return: ValueResponse
        """
        request.index += 1
        return super().get_response(request)
