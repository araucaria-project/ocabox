import logging
from typing import List

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.router.base_request_solver import BaseRequestSolver

logger = logging.getLogger(__name__)


class RequestSolver(BaseRequestSolver):

    def __init__(self, data_provider: ProvidesResponseProtocol, **kwargs):
        super(RequestSolver, self).__init__(data_provider, **kwargs)

    async def get_answer(self, request: List[dict]) -> List[dict]:
        # docstring is imported from parent
        response = []
        for r in request:
            # try to load data into ValueRequest object
            try:
                v_request = ValueRequest.from_dict(r)
            except (ValueError, AddressError, TypeError):
                # can not create ValueRequest object (data is damaged) - return empty response witch error
                logger.error('Can not convert request dictionary to request object.')
                re = ResponseError(4001, 'Can not build request from ordered data', repr(self))
                v_response = ValueResponse('', None, False, re)
                response.append(v_response.to_dict())
                continue
            # Can not find value provider application
            if not self.data_provider or not isinstance(self.data_provider, ProvidesResponseProtocol):
                logger.error('Can not find value provider application.')
                re = ResponseError(4002, '', repr(self), 'CRITICAL')
                v_response = ValueResponse('', None, False, re)
                response.append(v_response.to_dict())
                continue
            # try to get response
            # get_response method shouldn't raise any errors !!!
            try:
                v_response = await self.data_provider.get_response(v_request)
            except Exception as e:
                logger.error(f'{str(e)}')
                re = ResponseError(4002, '', repr(self), 'CRITICAL')
                v_response = ValueResponse('', None, False, re)
            response.append(v_response.to_dict())
        return response
