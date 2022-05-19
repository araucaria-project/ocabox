import logging
from typing import List

from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.data_colection.value_set import ValueSet

logger = logging.getLogger(__name__)


class ValueBroker:

    def __init__(self):
        self._list_providers: List[ValueSet] = []

    def get_response(self, request: ValueRequest) -> ValueResponse:
        provider = self._get_provider(request)
        if not provider:
            logger.warning(f'Unrecognised address: {request.address} lever: {request.index}')
            return ValueResponse(request.address, None)
        request.index += 1
        response = provider.get_response(request)
        return response

    def _get_provider(self, v_req: ValueRequest):
        """
        This method return provider for give address if is known.
        :param v_req:
        :return: return provider if exist or None if not
        """
        index = v_req.index
        address = v_req.address
        try:
            provider_name = address[index]
        except IndexError:
            provider_name = None
        if not provider_name:
            # logger.error(f'Wrong address: {str(address)}')
            return None
        provider = None
        for p in self._list_providers:
            if p.get_source_address() is provider_name:
                provider = p
                break
        return provider

    def add_provider(self, provider: ValueSet, force: bool = False):
        for p in self._list_providers:
            if p.get_source_address() == provider.get_source_address():
                if force:
                    logger.warning(f'One with the same address has already been found in the list of provider. '
                                   f'It will be removed from the list.')
                    self._list_providers.remove(p)
                else:
                    logger.warning(f'You cannot add a provider to the list because there is already a provider with '
                                   f'the same address on it. ')
                    return False
        self._list_providers.append(provider)
        return True

    def get_list_providers(self):
        return self._list_providers

    def remove_provider(self, provider: ValueSet):
        try:
            self._list_providers.remove(provider)
            return True
        except ValueError:
            logger.warning(f'Can not find given provider in the list.')
            return False
