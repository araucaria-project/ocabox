from __future__ import annotations

import confuse
import logging
import asyncio

from ob.comunication.base_client_api import BaseClientAPI
from ob.ob_config import SingletonConfig
from time import time
import os
import pwd
import socket
from typing import TYPE_CHECKING

from ob.util_functions.asyncio_util_functions import wait_for_psce
from ob.comunication.comunication_error import CommunicationTimeoutError, CommunicationRuntimeError

from ocaboxapi import ClientAPI
from ocaboxapi.exceptions import OcaboxServerError, OcaboxAccessDenied

if TYPE_CHECKING:
    from ocaboxapi.telescope import Telescope
    from ocaboxapi.ephemeris import Ephemeris

logger = logging.getLogger("observatory")


class Observatory:
    """The Observatory maintains connection to the single observatory server using `ocabox.Client`"""

    def __init__(self, client_name='DefaultClient', software_id=None) -> None:
        self._client = None
        self.client_name = client_name
        self.software_id = software_id
        self.telescopes = {}
        self.ephemeris = None
        self._subscribers = []
        super().__init__()

    def get_app_cfg(self, key: str, default=None):
        value = self.client.get_cfg_deep(["app", key])  # no use default option because we need a different order
        if value is None:
            value = default
        return value

    # def get_client_config(self, client_cfg: Optional[str] = None):
    #     """
    #     Gets OCABOX client config subtree for specified client name entry.
    #
    #     Do not confuze with ocabox-cli settings
    #     If `client_cfg`  not provided, we will try to take it form
    #     settings `ocabox/client_cfg` or take default `DefaultClient`
    #     """
    #     if client_cfg is None:
    #         try:
    #             client_cfg = settings.ocabox.client_cfg
    #         except LookupError:
    #             client_cfg = 'DefaultClient'
    #     return ClientAPI.client_config()['client'][client_cfg]

    def connect(self, client: BaseClientAPI | None = None):
        if client is None:
            host = socket.gethostname()
            user = pwd.getpwuid(os.getuid())[0]
            self._client = ClientAPI(name=self.client_name,
                                     user_name=f'{user}@{host}' + (
                                         f' [{self.software_id}]' if self.software_id else ''))
        else:
            self._client = client

    @property
    def client(self) -> BaseClientAPI:
        if self._client is None:
            self.connect()
        return self._client

    @property
    def time_of_data_tolerance(self):
        return self.client.get_cfg('time_of_data_tolerance', 0.5)

    def get_telescope(self, telescope_id: str):
        """Creates and gets telescope of specified id

        If telescope of specified id have been created already, it is returned, otherwise
        new Telescope instance is created, saved and returned"""
        try:
            return self.telescopes[telescope_id]
        except LookupError:
            from ocaboxapi.telescope import Telescope
            tele = Telescope(telescope_id, self)
            self.telescopes[telescope_id] = tele
            return tele

    def get_ephemeris(self) -> Ephemeris:
        if self.ephemeris is None:
            from ocaboxapi.ephemeris import Ephemeris
            self.ephemeris = Ephemeris(id='global.ephemeris', observatory=self)
        return self.ephemeris

    async def put_async(self, address: str,
                        time_of_data: float or None = None,
                        time_of_data_tolerance: float or None = None,
                        request_timeout: float or None = None,
                        parameters_dict: dict = None):

        """Sets value to specified address
        @param address: Address of requested value
        @param request_timeout: Timeout for request
        @return:
        """
        if request_timeout is None:
            request_timeout = time() + self.client.get_cfg('request_timeout', default=2.01)

        try:
            res = await self.client.put_async(f'{address}',
                                              time_of_data=time_of_data,
                                              # time_of_data_tolerance=time_of_data_tolerance,
                                              request_timeout=request_timeout,
                                              parameters_dict=parameters_dict,
                                              no_wait=False
                                              )
            logger.debug(f'client.put_async {address} returned result: {res}')
        except (CommunicationTimeoutError, CommunicationRuntimeError) as e:
            raise e

        if not res.status:
            if res.error.code == 1004:
                logger.info(f' {address}: {res.error.message}')
                raise OcaboxAccessDenied(f'Access Denied for {address}: {res.error}')
            else:
                raise OcaboxServerError(f'OCABOX error on {address}: {res.error}')
        try:
            ret = res.value.v
        except Exception as e:
            logger.error(f'Return value not exisit regardless status=True, when setting value to {address}: {e}')
            raise OcaboxServerError(f'Value error on {address}: {res.error}', e)
        return ret

    async def get_async(self, address: str,
                        time_of_data: float or None = None,
                        time_of_data_tolerance: float or None = None,
                        request_timeout: float or None = None,
                        parameters_dict: dict = None):
        """Gets value from specified address
        @param address: Address of requested value
        @param time_of_data:
        @param time_of_data_tolerance:
        @param request_timeout:
        @param parameters_dict:
        @return:
        """

        if time_of_data_tolerance is None:
            time_of_data_tolerance = self.client.get_cfg('time_of_data_tolerance', default=None)
        if request_timeout is None:
            request_timeout = time() + self.client.get_cfg('request_timeout', default=2.02)

        # TODO: Something with timeouts with default parameters
        try:
            res = await self.client.get_async(f'{address}',
                                              time_of_data=time_of_data,
                                              time_of_data_tolerance=time_of_data_tolerance,
                                              request_timeout=request_timeout,
                                              parameters_dict=parameters_dict)
            logger.debug(f'client.get_async {address} returned result: {res}')
        except (CommunicationTimeoutError, CommunicationRuntimeError) as e:
            raise e

        if not res.status:
            raise OcaboxServerError(f'OCABOX error on {address}: {res.error}')
        try:
            ret = res.value.v
        except Exception as e:
            logger.error(f'Return value not exisit regardless status=True when getting value from {address}: {e}')
            raise OcaboxServerError(f'Value error on {address}: {res.error}', e)

        return ret

    async def subscribe_async(self, address: str,
                              time_of_data_tolerance: float | None = None,
                              delay: float | None = None,
                              name: str | None = None,
                              max_missed_msg: int | None = None,
                              parameters_dict: dict = None,
                              callback_method=None,
                              async_callback_method=None
                              ):
        """Subscribes to specified address
        Blocks!
        @param address: Address of requested value
        @param time_of_data_tolerance:
        @param delay: minimum delay between pulling updated values
        @param parameters_dict: additional parameters for get
        """

        if time_of_data_tolerance is None:
            time_of_data_tolerance = self.client.get_cfg('time_of_data_tolerance', default=None)
        if delay is None:
            delay = self.client.get_cfg('delay', default=None)
        if name is None:
            name = f'Sub: {address}'
        if max_missed_msg is None:
            max_missed_msg = self.client.get_cfg('max_missed_msg', default=None)

        cq = await self.client.subscribe_with_callback(address,
                                                       time_of_data_tolerance=time_of_data_tolerance,
                                                       delay=delay,
                                                       parameters_dict=parameters_dict,
                                                       name=name,
                                                       max_missed_msg=max_missed_msg,
                                                       callback_method=callback_method,
                                                       async_callback_method=async_callback_method
                                                       )
        self._subscribers.append(cq)
        return cq

    def unsubscribe_all(self):
        for cq in self._subscribers:
            self.unsubscribe(cq)

    def unsubscribe(self, cq):
        del self._subscribers[self._subscribers.index(cq)]
        cq.stop()

    async def aunsubscribe_all(self):
        for cq in self._subscribers:
            await self.aunsubscribe_psce(cq)

    async def aunsubscribe_psce(self, cq):
        del self._subscribers[self._subscribers.index(cq)]
        cq.stop()
        time_to_close = 0.5
        try:

            await wait_for_psce(
                cq.stop_and_wait(),
                timeout=time_to_close
            )  # the task should finish in less than 0.5 seconds
        except asyncio.TimeoutError:
            pass

    async def is_tic_server_available(self, request_timeout: float = None):
        """
        The method checks if the server responds

        :param request_timeout: waiting for answer timeout
        :return: True if server responds
        """
        return await self.client.server_is_alive(request_timeout=request_timeout)

    async def subscribe_async_old(self, address: str, callback,
                                  time_of_data_tolerance: float | None = None,
                                  delay: float | None = None,
                                  name: str | None = None,
                                  max_missed_msg: int | None = None,
                                  parameters_dict: dict = None):
        """Subscribes to specified address
        Blocks!
        @param address: Address of requested value
        @param time_of_data_tolerance:
        @param delay: minimum delay between pulling updated values
        @param parameters_dict: additional parameters for get
        """

        if time_of_data_tolerance is None:
            time_of_data_tolerance = self.client.get_cfg('time_of_data_tolerance', default=None)
        if delay is None:
            delay = self.client.get_cfg('delay', default=None)
        if name is None:
            name = f'Sub: {address}'
        if max_missed_msg is None:
            max_missed_msg = self.client.get_cfg('max_missed_msg', default=None)

        cq = await self.client.subscribe(address,
                                         time_of_data_tolerance=time_of_data_tolerance,
                                         delay=delay,
                                         parameters_dict=parameters_dict,
                                         name=name,
                                         max_missed_msg=max_missed_msg
                                         )
        cq.start()
        try:
            while True:
                result = await cq.get_response()
                logger.debug(f'Got subscribed {address}')
                if result and result[0].value:
                    callback(result[0].value.v)
        except CommunicationRuntimeError as e:
            logger.error('Communication error: %s', e)
        finally:
            logger.info(f'Stopping {address} subscription...')
            cq.stop()

    def get(self, address: str,
            time_of_data: float or None = None,
            time_of_data_tolerance: float or None = None,
            request_timeout: float or None = None,
            parameters_dict: dict = None):
        """Gets value from specified address
        @param address: Address of requested value (without the telescope)
        @param time_of_data:
        @param time_of_data_tolerance:
        @param request_timeout:
        @param parameters_dict:
        @return:
        """
        ## TODO: maybe client should have synchronous version of get?
        logger.error('Synchronous get from `TelescopeComponent` and derived classes is not supported by '
                     'ocabox yet. Use `async_get` instead.')
        return 'n/a'
        raise CriticalErrorAbort(f'Synchronous get from `TelescopeComponent` and derived classes is not supported by '
                                 f'ocabox yet. Use `async_get` for {address} instead.')

        oldloop = asyncio.get_event_loop()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            future = asyncio.run(self.get_async(address,
                                                time_of_data=time_of_data,
                                                time_of_data_tolerance=time_of_data_tolerance,
                                                request_timeout=request_timeout,
                                                parameters_dict=parameters_dict))
            ret = future.result()

            # loop = asyncio.get_event_loop()
            # tsk  = loop.create_task(self.get_async(address,
            #                                   time_of_data=time_of_data,
            #                                   time_of_data_tolerance=time_of_data_tolerance,
            #                                   request_timeout=request_timeout,
            #                                   parameters_dict=parameters_dict)
            #                    )
        except Exception as e:
            logger.error(f'Error getting value from {address}: {e}')
            raise e
        finally:
            asyncio.set_event_loop(oldloop)
        return ret
