import logging
from typing import List

from ob.data_colection.base_components.address_dispatcher import AddressDispatcher
from ob.data_colection.base_components.tree_base_broker import TreeBaseBroker
from ob.data_colection.base_components.tree_component import AddressedResponderProtocol
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class TreeBroker(TreeBaseBroker, AddressDispatcher):
    """
    BX

    :param component_name: this is name of tree component, used for debug
    :param source_name: This is a component name with will be used to decode address
    :param list_providers: list all next providers in tree

    Conforms to:
        AddressedResponderProtocol
    """

    def __init__(self, component_name: str, source_name: str, list_providers: List[AddressedResponderProtocol] = None,
                 **kwargs):
        super().__init__(component_name=component_name, list_providers=list_providers, source_name=source_name,
                         **kwargs)

    async def get_response(self, request: ValueRequest) -> ValueResponse:
        # docstring is imported from parent
        # TODO Czy sprawdzać czy adres jest tego komponentu jest poprawny? Poprzedni elemęt decyduje gdzie wysłać
        #  zapytanie ale może oszukać czy sprawdzać to? MIKOŁAJ
        request.index += 1
        return await super().get_response(request)
