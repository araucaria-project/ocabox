import asyncio
import datetime
from typing import List

from ob.comunication.base_request_solver import BaseRequestSolver
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse


class SampleTestResolver(BaseRequestSolver):
    RESPONSE_DELAY = 0

    def __init__(self, data_provider: ProvidesResponseProtocol, **kwargs):
        self.response_delay = self.RESPONSE_DELAY
        super().__init__(data_provider, **kwargs)

    async def get_answer(self, request: List[dict]) -> List[dict]:
        response = []
        for req in request:
            v_request = ValueRequest.from_dict(req)
            response.append(ValueResponse(v_request.address, Value('sample_answer', datetime.datetime.now())).to_dict())
        await asyncio.sleep(self.response_delay)
        return response
