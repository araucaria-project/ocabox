import logging
from typing import List

from ob.data_colection.base_components.address_dispatcher import AddressDispatcher
from ob.data_colection.address import AddressError
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class ValueBroker(AddressDispatcher):

    def __init__(self, source_name: str, list_providers: List[AddressDispatcher] = None):
        super().__init__(source_name)
        self._list_providers: List[AddressDispatcher] = list_providers if list_providers and isinstance(list_providers,
                                                                                                        list) else []

    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.
        If request is correct but broker can't find data provider then return empty answer
        :param request:
        :return:
        """
        try:
            provider = self._get_provider(request)  # Here can raise AddressError
        except AddressError as e:
            re = ResponseError(e.code, '', self._source_name)
            logger.info(f'Wrong format request address {request.address} - make error response')
            return ValueResponse(request.address, None, False, re)  # address is damaged
        if not provider:
            re = ResponseError(1002, '', self._source_name)
            logger.info(f'Unrecognised provider: {request.address} lever: {request.index}')
            return ValueResponse(request.address, None, False, re)  # address is unknown
        request.index += 1
        response = provider.get_response(request)
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
            raise AddressError(address, 1001)
        provider = None
        for p in self._list_providers:
            if p.get_source_name() == provider_name:
                provider = p
                break
        return provider

    def add_provider(self, provider: AddressDispatcher, force: bool = False):
        for p in self._list_providers:
            if p.get_source_name() == provider.get_source_name():
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

    def remove_provider(self, provider: AddressDispatcher):
        try:
            self._list_providers.remove(provider)
            return True
        except ValueError:
            logger.warning(f'Can not find given provider in the list.')
            return False
