import logging
from typing import List

from ob.data_colection.address import AddressError
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.data_colection.value_set import ValueSet

logger = logging.getLogger(__name__)


class ValueBroker:

    def __init__(self, list_providers: List[ValueSet] = None):
        self._list_providers: List[ValueSet] = list_providers if list_providers and \
                                                                 isinstance(list_providers, list) else []

    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.
        If request has incorrect (wrong format or wrong type) address this method raise AddressError
        If request is correct but broker can't find data provider then return empty answer
        :param request:
        :return:
        """
        provider = self._get_provider(request)  # Here can raise AddressError
        if not provider:
            logger.warning(f'Unrecognised address: {request.address} lever: {request.index}')
            return ValueResponse(request.address, None)
            # TODO Don't known provider, return empty response or raise
            #  error and don't ansvear MIKOŁAJ
            # raise AddressError(request.address, message=f'Wrong address <{str(request.address)}> . Unknown provider')
        request.index += 1
        response = provider.get_response(request)  # Here can raise AddressError
        return response

    def _get_provider(self, v_req: ValueRequest):
        """
        This method return provider for give address if is known.
        If request has incorrect address this method raise AddressError
        :param v_req:
        :return: return provider if exist or None if not
        """
        index = v_req.index
        address = v_req.address
        try:
            provider_name = address[index]
        except IndexError:
            raise AddressError(address)
        provider = None
        for p in self._list_providers:
            if p.get_source_address() == provider_name:
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
