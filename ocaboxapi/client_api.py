import logging
from typing import List

from obcom.comunication.base_client_api import BaseClientAPI
from obcom.comunication.cycle_query import BaseCycleQuery
from obcom.data_colection.address import Address
from obcom.data_colection.value_call import ValueRequest
from ob.comunication.client import Client
from ob.comunication.client_request_solver import ClientRequestSolver
from ob.comunication.cycle_query import ConditionalCycleQuery, PeriodicCycleQuery
from obcom.data_colection.tree_user import TreeUser, BaseTreeUser

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ClientAPI(BaseClientAPI):

    def __init__(self, name: str = None, client: Client = None, user_name: str = '', user_description: str = '',
                 user_email: str = '', **kwargs):
        self._crs = ClientRequestSolver(name=name, client=client)
        self._user = TreeUser(email=user_email,
                              name=user_name if user_name else self._crs.client.name,
                              description=user_description)
        super().__init__(**kwargs)

    @property
    def user(self) -> BaseTreeUser:
        return self._user

    @property
    def _CRS(self) -> ClientRequestSolver:  # todo tu jest zmiana typu po dziedziczeniu - sprawdzić czy jest to poprawne
        return self._crs

    def get_client(self):
        return self._CRS.client

    async def server_is_alive(self, request_timeout: float = None) -> bool:
        """
        The method checks if the server responds

        :param request_timeout: waiting for answer timeout
        :return: True if server responds
        """
        return await self._CRS.ping_server(request_timeout=request_timeout)

    async def server_reload_nats_config(self, request_timeout: float = None) -> bool:
        """
        The method sends a request to the server to resend the configuration to nats.

        :param request_timeout: waiting for answer timeout
        :return: True if success
        """
        return await self._CRS.reload_nats_config(request_timeout=request_timeout)

    def get_cfg(self, name_cfg: str, default=None, use_default_settings=True):
        #TODO: deprecated method
        return default

    def get_cfg_deep(self, name_cfg: List[str], default=None, use_default_settings=True):
        #TODO: deprecated method
        return default

    async def subscribe(self, address: str | Address, time_of_data_tolerance: float | None = None,
                        delay: float | None = None, parameters_dict: dict = None,
                        name: str = 'Default_subscription', max_missed_msg: int = None,
                        ignore_errors: bool = False) -> BaseCycleQuery:
        """Create a :class:`~ob.comunication.cycle_query.ConditionalCycleQuery` subscription.

        Returns an extended :class:`~ob.comunication.cycle_query.ConditionalCycleQuery` that
        supports optional error callbacks (see
        :meth:`~ob.comunication.cycle_query.BaseCycleQuery.add_error_callback_method` and
        :meth:`~ob.comunication.cycle_query.BaseCycleQuery.add_async_error_callback_method`).

        :param address: address to subscribe to
        :param time_of_data_tolerance: staleness tolerance in seconds
        :param delay: minimum interval between responses in seconds
        :param parameters_dict: additional request parameters
        :param name: human-readable subscription name used in log lines
        :param max_missed_msg: missed-message budget before terminal stop
        :param ignore_errors: treat non-temporary errors as retryable
        :return: :class:`~ob.comunication.cycle_query.ConditionalCycleQuery`
        """
        if time_of_data_tolerance is None and delay:
            time_of_data_tolerance = delay
        if parameters_dict is None:
            parameters_dict = {}
        request = ValueRequest(address=address,
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_data=parameters_dict,
                               user=self.user)
        cq = ConditionalCycleQuery(crs=self._CRS, list_request=[request], delay=delay,
                                   max_missed_msg=max_missed_msg, query_name=name,
                                   ignore_errors=ignore_errors)
        return cq

    async def send_cycle_multipart(self, address: str | Address,
                                   time_of_data_tolerance: float | None = None,
                                   delay: float | None = None, parameters_dict: dict = None,
                                   name: str = 'Default_cycle_request', max_missed_msg: int = None,
                                   log_missed_msg: bool = False) -> BaseCycleQuery:
        """Create a :class:`~ob.comunication.cycle_query.PeriodicCycleQuery`.

        Returns an extended :class:`~ob.comunication.cycle_query.PeriodicCycleQuery` that
        supports optional error callbacks.

        :param address: address to query
        :param time_of_data_tolerance: staleness tolerance in seconds
        :param delay: minimum interval between responses in seconds
        :param parameters_dict: additional request parameters
        :param name: human-readable query name used in log lines
        :param max_missed_msg: missed-message budget before terminal stop
        :param log_missed_msg: emit a warning on each missed message
        :return: :class:`~ob.comunication.cycle_query.PeriodicCycleQuery`
        """
        if not time_of_data_tolerance and delay:
            time_of_data_tolerance = delay
        if parameters_dict is None:
            parameters_dict = {}
        request = ValueRequest(address=address,
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_data=parameters_dict,
                               user=self.user)
        cq = PeriodicCycleQuery(crs=self._CRS, list_request=[request], delay=delay,
                                max_missed_msg=max_missed_msg, query_name=name,
                                log_missed_msg=log_missed_msg)
        return cq
