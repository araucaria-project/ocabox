import asyncio
import logging
from typing import List
from abc import ABC, abstractmethod
from ob.data_colection.response_error import ResponseError
from ob.data_colection.tree_user import TreeUser, TreeServiceUser
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol

logger = logging.getLogger(__name__.rsplit('.')[-1])


class BaseRequestSolver(ABC):

    def __init__(self, data_provider: ProvidesResponseProtocol, **kwargs):
        self.data_provider: ProvidesResponseProtocol = data_provider

    @abstractmethod
    async def get_answer(self, request: List[bytes], user_id: bytes, timeout=None) -> List[bytes]:
        """
        This method is designed to provide a response to given request by calling to data_provider. The received query
        is a list of minor queries for single values. This method runs a separate task for each query in order to
        reduce the waiting time. Created tasks are associated with this method and if the task that called this method
        is canceled, all tasks created by it will also be canceled.

        :param request: List of bytes representing ValueRequest
        :param user_id: User id
        :param timeout: request timeout
        :return: List of bytes representing ValueResponse
        """
        pass

    @abstractmethod
    async def get_single_answer(self, request: bytes, user_id: bytes, timeout=None) -> bytes:
        """
        The method reads the query details and calls the provider for an answer for a single query.

        :param request: bytes representing ValueRequest
        :param user_id: User id
        :param timeout: request timeout
        :return: bytes representing ValueResponse
        """
        pass

    async def run_tree(self):
        """
        This method starts cascading asynchronous tree initialization.

        :return:
        """
        await self.data_provider.run()

    async def stop_tree(self):
        """
        This method stops cascading asynchronous tree elements.

        :return:
        """
        await self.data_provider.stop()

    async def get_answer_internal(self, request: List[ValueRequest], timeout=None) -> List[ValueResponse]:
        response = []
        coroutines = []
        for r in request:
            coroutines.append(self.get_single_answer_internal(r, timeout=timeout))
        result = await asyncio.gather(*coroutines, return_exceptions=True)
        for r in result:
            if not isinstance(r, Exception):
                response.append(r)
            else:
                logger.error(f"CRITICAL One of the sub-tasks raise some unresolved exception.")
                re = ResponseError(4001, 'There were unexpected problems trying to respond to the request', repr(self),
                                   ResponseError.SEVERITY_CRITICAL)
                v_response = ValueResponse('', None, False, re)
                response.append(v_response)
        return response

    async def get_single_answer_internal(self, v_request: ValueRequest, timeout=None) -> ValueResponse:
        if isinstance(v_request.user, TreeUser):
            logger.warning(f'Internal request has normal ({TreeUser.__name__}) user instance, should be '
                           f'{TreeServiceUser.__name__} instead. Will be created new correct user and will be change')
            v_request.user = TreeServiceUser(**v_request.user.to_dict())
        if v_request.request_timeout != timeout and timeout:
            v_request.request_timeout = timeout
        v_response = await self._get_single_answer(v_request=v_request)
        return v_response

    async def _get_single_answer(self, v_request: ValueRequest):
        # Can not find value provider application
        if not self.data_provider or not isinstance(self.data_provider, ProvidesResponseProtocol):
            logger.error('Can not find value provider application.')
            re = ResponseError(4002, '', repr(self), ResponseError.SEVERITY_CRITICAL)
            v_response = ValueResponse(v_request.address, None, False, re)
            return v_response
        # try to get response
        # get_response method shouldn't raise any errors !!!
        try:
            v_response = await self.data_provider.get_response(v_request)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f'{str(e)}')
            re = ResponseError(4002, '', repr(self), ResponseError.SEVERITY_CRITICAL)
            v_response = ValueResponse(v_request.address, None, False, re)
        return v_response
