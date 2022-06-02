import logging

from ob.data_colection.base_components.tree_base_provider import TreeBaseProvider
from ob.data_colection.base_components.tree_component import TreeComponent
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class TreeProvider(TreeBaseProvider):
    """
    PX
    """
    def __init__(self, component_name: str, source_name: str, subcontractor: TreeComponent = None, **kwargs):
        super().__init__(component_name=component_name, subcontractor=subcontractor, source_name=source_name, **kwargs)

    def get_value(self, request: ValueRequest) -> Value or None:
        raise NotImplementedError

    def get_response(self, request: ValueRequest) -> ValueResponse:
        request.index += 1
        return super().get_response(request)
