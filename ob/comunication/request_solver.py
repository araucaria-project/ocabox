import asyncio
import logging
from typing import List

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.comunication.base_request_solver import BaseRequestSolver

logger = logging.getLogger(__name__)


class RequestSolver(BaseRequestSolver):

    def __init__(self, data_provider: ProvidesResponseProtocol, **kwargs):
        super(RequestSolver, self).__init__(data_provider, **kwargs)

    async def get_answer(self, request: List[dict]) -> List[dict]:
        # docstring is imported from parent
        response = []
        coroutines = []
        for r in request:
            coroutines.append(self.get_single_answer(r))
        result = await asyncio.gather(*coroutines, return_exceptions=True)
        for r in result:
            if not isinstance(r, Exception):
                response.append(r)
            else:
                # This is a precaution against unexpected program failures. To run properly, all errors should be
                # caught in '_get_single_answer' method.
                logger.error(f"CRITICAL One of the sub-tasks raise some unresolved exception.")
                re = ResponseError(4001, 'There were unexpected problems trying to respond to the request', repr(self),
                                   'CRITICAL')
                v_response = ValueResponse('', None, False, re)
                resp = v_response.to_dict()
                response.append(resp)
        return response

    async def get_single_answer(self, request: dict) -> dict:
        # docstring is imported from parent
        response: dict
        try:
            v_request = ValueRequest.from_dict(request)
        except (ValueError, AddressError, TypeError):
            # can not create ValueRequest object (data is damaged) - return empty response witch error
            logger.info('Can not convert request dictionary to request object.')
            re = ResponseError(4001, 'Can not build request from ordered data', repr(self), 'CRITICAL')
            v_response = ValueResponse('', None, False, re)
            response = v_response.to_dict()
            return response
        # Can not find value provider application
        if not self.data_provider or not isinstance(self.data_provider, ProvidesResponseProtocol):
            logger.error('Can not find value provider application.')
            re = ResponseError(4002, '', repr(self), 'CRITICAL')
            v_response = ValueResponse(v_request.address, None, False, re)
            response = v_response.to_dict()
            return response
        # try to get response
        # get_response method shouldn't raise any errors !!!
        try:
            v_response = await self.data_provider.get_response(v_request)
        except Exception as e:
            logger.error(f'{str(e)}')
            re = ResponseError(4002, '', repr(self), 'CRITICAL')
            v_response = ValueResponse(v_request.address, None, False, re)
        response = v_response.to_dict()
        return response
