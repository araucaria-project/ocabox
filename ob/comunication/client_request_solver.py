import logging
from typing import List, Optional

from ob.comunication.base_client_request_solver import BaseClientRequestSolver
from ob.comunication.client import Client
from ob.comunication.comunication_error import CommunicationRuntimeError, CommunicationTimeoutError
from ob.data_colection.address import AddressError
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ClientRequestSolver(BaseClientRequestSolver):

    def __init__(self, name: str = None, client: Client = None):
        super().__init__(**kwargs)
        self._client = client if client else Client(name=name)

    @property
    def client(self):
        return self._client

    async def send_request(self, requests: List[ValueRequest], timeout: float = None,
                           no_wait: bool = False) -> Optional[List[ValueResponse]]:
        """

        :param requests: list of requests
        :param timeout: request timeout, by after that will raise CommunicationTimeoutError
        :param no_wait: no wait for response flag
        :raise CommunicationRuntimeError:
        :raise CommunicationTimeoutError:
        :return: list of responses
        """
        request_b = [r.to_byte() for r in requests]
        try:
            resp = await self.client.send_multipart(request_b, request_timeout=timeout, no_wait=no_wait)
        except CommunicationRuntimeError:
            raise
        except CommunicationTimeoutError:
            raise
        if resp is None:
            return None
        vr = []
        for r in resp:
            try:
                vr.append(ValueResponse.from_byte(r))
            except (ValueError, AddressError, TypeError):
                # can not create ValueRequest object (data is damaged) - return empty response witch error
                logger.info('Can not convert request dictionary to request object.')
                re = ResponseError(4001, 'Can not build request from ordered data', repr(self.client),
                                   ResponseError.SEVERITY_CRITICAL)
                vr.append(ValueResponse('', None, False, re))
        return vr

    async def ping_server(self, request_timeout: float = None):
        """
        The method checks if the server responds

        :param request_timeout: waiting for answer timeout
        :return: True if server responds
        """
        result = await self.client.ping_server(request_timeout=request_timeout)
        return result is not None

    def get_cfg(self, name_cfg: str, default=None, use_default_settings=True):
        return self.client.get_cfg(name_cfg=name_cfg, default=default, use_default_settings=use_default_settings)
