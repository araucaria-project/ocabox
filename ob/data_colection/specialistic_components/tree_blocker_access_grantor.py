import logging

from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__)


class TreeBlockerAccessGrantor(TreeProvider):

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        pass
