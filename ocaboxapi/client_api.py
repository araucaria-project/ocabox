import logging
from typing import List

from obcom.comunication.base_client_api import BaseClientAPI
from ob.comunication.client import Client
from ob.comunication.client_request_solver import ClientRequestSolver
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

    def get_cfg(self, name_cfg: str, default=None, use_default_settings=True):
        return self._CRS.get_cfg(name_cfg, default, use_default_settings)

    def get_cfg_deep(self, name_cfg: List[str], default=None, use_default_settings=True):
        return self._CRS.client.get_cfg_deep(name_cfg=name_cfg, default=default,
                                             use_default_settings=use_default_settings)

    async def server_is_alive(self, request_timeout: float = None):
        """
        The method checks if the server responds

        :param request_timeout: waiting for answer timeout
        :return: True if server responds
        """
        return await self._CRS.ping_server(request_timeout=request_timeout)
