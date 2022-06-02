import logging
from typing import List, Protocol

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.address_dispatcher import AddressDispatcher, AddressedProtocol
from ob.data_colection.base_components.tree_component import TreeComponent, ProvidesResponseProtocol
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class AddressedResponderProtocol (ProvidesResponseProtocol, AddressedProtocol, Protocol):
    pass


class TreeBaseBroker(TreeComponent):
    """
    B0
    """

    def __init__(self, component_name: str, list_providers: List[AddressedResponderProtocol] = None, **kwargs):
        super().__init__(component_name=component_name, **kwargs)
        # TODO jak typowć podwójne klasy bo potrzebuje żeby było jednocześnie TreeComponent and AddressDispatcher
        self._list_providers: List[AddressedResponderProtocol] = \
            list_providers if list_providers and isinstance(list_providers, list) else []

    def get_response(self, request: ValueRequest) -> ValueResponse:
        """
        This method return response for given request.
        :param request: ValueRequest
        :return: ValueResponse
        """
        ss: TreeComponent and AddressDispatcher
        try:
            provider = self._get_provider(request)  # Here can raise AddressError
        except AddressError:
            re = ResponseError(1001, '', repr(self))
            logger.info(f'Wrong format request address {request.address} - make error response')
            return ValueResponse(request.address, None, False, re)  # address is damaged
        if not provider:
            re = ResponseError(1002, '', repr(self))
            logger.info(f'Unrecognised provider: {request.address} lever: {request.index}')
            return ValueResponse(request.address, None, False, re)  # address is unknown
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
            raise AddressError(address)
        provider = None
        for p in self._list_providers:
            if p.get_source_name() == provider_name:
                provider = p
                break
        return provider

    def add_provider(self, provider: AddressedResponderProtocol, force: bool = False):
        """
        This method add new provider to list
        :param provider: provider
        :param force: if true, method add provider even if exist provider with the same source name and remove old
        provider. Default false
        :return: True if success remove and false if not
        """
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
        """
        Method return all providers
        :return: list all providers
        """
        return self._list_providers

    def remove_provider(self, provider: AddressedResponderProtocol):
        """
        This method remove given provider from list providers
        :param provider: provider to remove from list
        :return: True if success remove and false if not
        """
        try:
            self._list_providers.remove(provider)
            return True
        except ValueError:
            logger.warning(f'Can not find given provider in the list.')
            return False
