import logging

from ob.data_colection.base_components.tree_component import AddressedResponderProtocol
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class TreeProviderFrontend(TreeProvider):

    COMPONENT_DEFAULT_NAME: str = 'TreeProviderFrontend'

    def __init__(self, component_name: str, subcontractor: AddressedResponderProtocol = None,
                 **kwargs):
        if subcontractor:
            source_name = subcontractor.get_source_name()
        else:
            logger.warning(f'No subcontractor has been indicated, this module {type(self).__name__} is '
                           f'closely related to its subcontractor and will not work properly without it.')
            source_name = 'no_named'
        super().__init__(component_name=component_name, subcontractor=subcontractor, source_name=source_name, **kwargs)
        # TODO zapytać o to jak zmienić typ na wyższy w klasie dziecka bez robienia @property MIKOŁAJ
        self._subcontractor: AddressedResponderProtocol = subcontractor

    # @property
    # def _subcontractor(self):
    #     return None

    def get_source_name(self) -> str:
        """
        The method returns the name of the subcontractor to use when decoding the query address.
        This class copies the name from the subcontractor.

        :return: name of that component with will be used to decode address
        """
        if self._subcontractor:
            return self._subcontractor.get_source_name()
        else:
            return self._source_name

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        # docstring is imported from parent
        return await super(TreeProvider, self).get_value(request=request)

    async def get_response(self, request: ValueRequest) -> ValueResponse:
        # docstring is imported from parent
        return await super(TreeProvider, self).get_response(request)

