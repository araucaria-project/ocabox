import logging
from typing import List
from ob.comunication.client import Client
from ob.comunication.comunication_error import CommunicationTimeoutError, CommunicationRuntimeError
from ob.data_colection.address import AddressError
from ob.data_colection.response_error import ResponseError
from ob.data_colection.tree_user import TreeUser
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class ClientAPI:

    def __init__(self, name: str = None, client: Client = None, user_name: str = '', user_description: str = '',
                 user_email: str = ''):
        self.client = client if client else Client(name=name)
        self.user = TreeUser(email=user_email,
                             name=user_name if user_name else self.client.name,
                             description=user_description)

    async def get_async(self, address, time_of_data: float or None = None,
                        time_of_data_tolerance: float or None = None,
                        request_timeout: float or None = None, parameters_dict: dict = None):
        if parameters_dict is None:
            parameters_dict = {}
        request = ValueRequest(address=address,
                               time_of_data=time_of_data,
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_timeout=request_timeout,
                               request_data=parameters_dict,
                               user=self.user)
        return await self.send_single(request)

    async def put_async(self, address, time_of_data: float or None = None,
                        time_of_data_tolerance: float or None = None,
                        request_timeout: float or None = None, parameters_dict: dict = None, no_wait=True):
        if parameters_dict is None:
            parameters_dict = {}
        request = ValueRequest(address=address,
                               time_of_data=time_of_data,
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_timeout=request_timeout,
                               request_type='PUT',
                               request_data=parameters_dict,
                               user=self.user)
        return await self.send_single(request, no_wait=no_wait)

    async def send_single(self, request: ValueRequest, no_wait: bool = False) -> ValueResponse or None:
        vr = await self.send_multi([request], no_wait=no_wait)
        if not no_wait:
            return vr[0]
        return None

    async def send_multi(self, requests: List[ValueRequest], no_wait: bool = False) -> List[ValueResponse] or None:
        """

        :param no_wait: If 'true' than request will be sent and client will not wait for response
        :param requests: request
        :raise CommunicationRuntimeError:
        :raise CommunicationTimeoutError:
        :return:
        """

        shortest_timeout = None
        request_b = []
        for r in requests:
            if r.request_timeout and (shortest_timeout is None or r.request_timeout < shortest_timeout):
                shortest_timeout = r.request_timeout
            if not r.user:
                r.user = self.user
            request_b.append(r.to_byte())
        if shortest_timeout is None:
            logger.error(f"Unable to get timeout value from request. Request is uncompleted.")
        try:
            resp = await self.client.send_multipart(request_b, request_timeout=shortest_timeout, no_wait=no_wait)
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
                re = ResponseError(4001, 'Can not build request from ordered data', repr(self.client), 'CRITICAL')
                vr.append(ValueResponse('', None, False, re))
        return vr
