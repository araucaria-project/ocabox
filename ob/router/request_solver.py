import logging
from typing import List

from ob.data_colection.coded_error import AddressError
from ob.data_colection.value_broker import ValueBroker
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.router.request_solver_interface import RequestSolverInterface

logger = logging.getLogger(__name__)


class RequestSolver(RequestSolverInterface):

    def __init__(self, data_provider: ValueBroker):
        self.data_provider: ValueBroker = data_provider

    async def get_answer(self, request: List[dict]) -> List[dict]:
        # TODO zabezpieczyć się przed NotImplementedError
        response = []
        for r in request:
            try:
                v_request = ValueRequest.from_dict(r)
            except (ValueError, AddressError):  # TODO na razie zostaje przechwytywanie  ale jak ValueRequest zacznie obsługiwać błędy to zmienić to
                logger.error('Can not convert request dictionary to request object.')
                raise ValueError
            # TODO tutaj powinien przechwycic błędy z providera i jeśli sa spowodowane złym zapytaniem to
            #  wypluć ValueError (na złe pytania nie odpowiadamy) a jeśli płyną ze złej konfiguracji to nasza wina
            #  więc coś trzeba odpowiedzieć. a może nie trzeba? MIKOŁAJ
            try:
                v_response = self.data_provider.get_response(v_request)
            except AddressError:
                #  raise ValueError because some part of request is incorrect so don't answer for this request
                raise ValueError
            response.append(v_response.to_dict())
        return response
