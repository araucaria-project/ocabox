from __future__ import annotations

import logging
import asyncio

import warnings

from obcom.comunication.base_client_api import BaseClientAPI
from obcom.comunication import timing
from obcom.comunication.error_policy import ErrorPolicy, ValuePolicy
from obcom.data_colection.value_call import ValueRequest
from time import time
import os
import pwd
import socket
from typing import TYPE_CHECKING, Optional

from ob.comunication.client import Client
from ob.comunication.nats_cfg_loader import NatsCfgLoader
from obcom.comunication.comunication_error import CommunicationTimeoutError, CommunicationRuntimeError

from ocaboxapi import ClientAPI
from ocaboxapi.exceptions import OcaboxError, OcaboxServerError
from ocaboxapi.read_policy import OnReadError

if TYPE_CHECKING:
    from ocaboxapi.telescope import Telescope
    from ocaboxapi.ephemeris import Ephemeris

logger = logging.getLogger("observatory")


class Observatory:
    """The Observatory maintains connection to the single observatory server using `ocabox.Client`"""

    #: string aliases accepted wherever a policy is expected
    POLICY_PRESETS = {
        'interactive': ErrorPolicy.INTERACTIVE,
        'service': ErrorPolicy.SERVICE,
        'display': ErrorPolicy.DISPLAY,
        'fail_fast': ErrorPolicy.FAIL_FAST,
    }

    def __init__(self, client_name='DefaultClient', software_id=None, config_stream: str = None,
                 use_fallback_file=False, fallback_file_for_config: str = None,
                 on_read_error: OnReadError | str | None = None,
                 policy: ErrorPolicy | str | None = None,
                 time_of_data_tolerance: float | None = None,
                 max_data_age: float | None = None) -> None:
        self._client = None
        self.client_name = client_name
        self.software_id = software_id
        # ----- Unified read policy (Staleness Contract, ocabox-common#8) -----
        # One object declares the client's identity for both axes: how the
        # transport nurses errors (per-severity actions, subscriptions) and
        # what the client receives once a value breaks its own tolerance
        # (value_policy: RAISE / NONE / LAST_GOOD). Presets: INTERACTIVE
        # (scripts/CLI), SERVICE (daemons), DISPLAY (GUIs — declares NONE
        # on the wire, requires ocabox-server >= 2.6 on the way to devices).
        #
        # ``on_read_error`` is a deprecated alias: it maps onto the local
        # value semantics only and deliberately does NOT declare a policy on
        # the wire, so a legacy client upgraded to this line stays safe
        # against pre-2.5.2 servers (the 2.3.12 unknown-field bug class).
        if policy is not None and on_read_error is not None:
            raise ValueError("Pass either 'policy' or the deprecated 'on_read_error', not both")
        self._value_policy_local: ValuePolicy
        if on_read_error is not None:
            warnings.warn(
                "'on_read_error' is deprecated; use policy=ErrorPolicy presets "
                "(e.g. Observatory(policy='display')) — OnReadError maps onto its value_policy axis.",
                DeprecationWarning, stacklevel=2)
            mapped = OnReadError(on_read_error)
            self._policy = ErrorPolicy.INTERACTIVE
            self._value_policy_local = {
                OnReadError.RAISE: ValuePolicy.RAISE,
                OnReadError.STALE: ValuePolicy.LAST_GOOD,
                OnReadError.NONE: ValuePolicy.NONE,
            }[mapped]
        elif policy is None:
            # The flip announced through the 2.6 line: an undeclared client
            # now gets the honest default — failed/stale reads RAISE.
            self._policy = ErrorPolicy.INTERACTIVE
            self._value_policy_local = ValuePolicy.RAISE
            logger.warning(
                f"Observatory({client_name!r}): no policy set — defaulting to INTERACTIVE/RAISE "
                f"(as announced, the pre-2.7 implicit STALE is gone: failed or stale reads now "
                f"raise). Pass policy='interactive'|'service'|'display' or an ErrorPolicy to "
                f"declare this client's identity explicitly.")
        else:
            if isinstance(policy, str):
                try:
                    policy = self.POLICY_PRESETS[policy.lower()]
                except KeyError:
                    raise ValueError(f"Unknown policy preset {policy!r}; "
                                     f"expected one of {sorted(self.POLICY_PRESETS)}")
            if not isinstance(policy, ErrorPolicy):
                raise ValueError(f"policy must be an ErrorPolicy or preset name, got {type(policy)}")
            self._policy = policy
            self._value_policy_local = policy.value_policy or ValuePolicy.RAISE
        # Temporal model (Staleness Contract): T1 = time_of_data_tolerance —
        # preferred freshness / refresh threshold where no per-call tolerance
        # exists; T2 = max_data_age — the truth bound: data older than T2 must
        # not be presented. Defaults: T1 ``timing.DEFAULT_REFRESH_AFTER`` (the one
        # family default, cache and wire alike), T2 by the family rule
        # ``ValueRequest.default_max_age`` (2*T1, floored). The client config
        # (``client.<name>.time_of_data_tolerance``) overrides T1 on the wire;
        # without it the wire gets this very T1, never a library default.
        self._time_of_data_tolerance = (timing.DEFAULT_REFRESH_AFTER if time_of_data_tolerance is None
                                        else float(time_of_data_tolerance))
        # An EXPLICIT observatory-wide T2 is inherited by subscriptions; the
        # derived default is not — each
        # subscription then gets 2x its own tolerance from the library.
        self._max_data_age_explicit = max_data_age is not None
        if max_data_age is None:
            self._max_data_age = ValueRequest.default_max_age(self._time_of_data_tolerance)
        else:
            self._max_data_age = max(float(max_data_age), self._time_of_data_tolerance)
        self.telescopes = {}
        self.ephemeris = None
        self._subscribers = []
        self._nats_cfg_loader = NatsCfgLoader(config_stream, use_file=use_fallback_file,
                                              fallback_file=fallback_file_for_config)
        super().__init__()

    @property
    def policy(self) -> ErrorPolicy:
        """The client's unified read policy — set once in the constructor,
        read-only so it cannot drift. Subscriptions inherit it as their
        default error_policy; GET/property reads enforce its value axis."""
        return self._policy

    @property
    def value_policy(self) -> ValuePolicy:
        """Effective truth axis for GET/property enforcement (never None —
        an undeclared policy behaves as RAISE, the 2.7 default)."""
        return self._value_policy_local

    @property
    def on_read_error(self) -> OnReadError:
        """Deprecated alias view of :meth:`value_policy` (kept for the 2.6
        line's callers): RAISE→RAISE, NONE→NONE, LAST_GOOD→STALE."""
        return {ValuePolicy.RAISE: OnReadError.RAISE,
                ValuePolicy.NONE: OnReadError.NONE,
                ValuePolicy.LAST_GOOD: OnReadError.STALE}[self._value_policy_local]

    async def load_client_cfg(self, timeout: Optional[float] = None):
        """
        Method load config of Client from nats server. This method should be run once after create Observatory object.
        """
        await self._nats_cfg_loader.load_cfg(timeout=timeout)

    def get_client_configuration(self) -> dict:
        """
        Method return configuration of client. First looking configuration in NATS if not find return default
        local configuration
        """
        if self._nats_cfg_loader and self._nats_cfg_loader.get_cfg():
            return self._nats_cfg_loader.get_cfg()
        return {}

    def get_telescopes_configuration(self) -> dict:
        """"Method return configuration for all telescopes. Return section telescopes from configuration from nats"""
        return self.get_client_configuration().get("telescopes", {})

    def _get_client_connection_cfg_from_nats(self) -> dict:
        return self._nats_cfg_loader.get_cfg_connection_client(
            self.client_name) if self._nats_cfg_loader is not None else {}

    def _get_client_config(self) -> dict:
        return self._nats_cfg_loader.get_cfg_client(self.client_name) if self._nats_cfg_loader is not None else {}

    def get_app_cfg(self, key: str, default=None):
        cfg = self._get_client_config()
        value = cfg.get("app", {}).get(key)
        if value is None:
            value = default
        return value

    def connect(self, client: BaseClientAPI | None = None, ocabox_server_host: str | None = None, ocabox_server_port: int | None = None):
        if client is None:
            host = socket.gethostname()
            user = pwd.getpwuid(os.getuid())[0]
            cfg = self._get_client_connection_cfg_from_nats()
            if ocabox_server_host is None:
                ocabox_server_host = cfg.get("url", None)
            if ocabox_server_port is None:
                ocabox_server_port = cfg.get("port", None)

            c = Client(name=self.client_name, port=ocabox_server_port, host=ocabox_server_host)
            self._client = ClientAPI(name=self.client_name,
                                     client=c,
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
        """T1: default preferred freshness (s) for reads without a per-call tolerance."""
        return self._time_of_data_tolerance

    @property
    def max_data_age(self):
        """T2: the truth bound (s) — data older than this must not be presented."""
        return self._max_data_age

    def get_telescope(self, telescope_id: str):
        """Creates and gets telescope of specified id

        If telescope of specified id have been created already, it is returned, otherwise
        new Telescope instance is created, saved and returned"""
        try:
            t = self.telescopes[telescope_id]
            # logger.error(f'========DOME FANS reusing  telescope {telescope_id} object {t}')
            return t
        except LookupError:
            from ocaboxapi.telescope import Telescope
            tele = Telescope(telescope_id, self)
            self.telescopes[telescope_id] = tele
            # logger.error(f'========DOME FANS new  telescope {telescope_id} object {tele}')
            return tele

    def dischard_cached_telescope(self, telescope: str | Telescope):
        """Dischards cached telescope instance by its id or by instance"""
        # logger.error(f'========DOME FANS discarding telescope {telescope}')
        if telescope in self.telescopes:
            del self.telescopes[telescope]
            # logger.error(f'========DOME FANS discarded telescope by id {telescope}')
        else:
            for key, val in list(self.telescopes.items()):
                if val == telescope:
                    del self.telescopes[key]
                    # logger.error(f'========DOME FANS discarded telescope {telescope.id} object:  {telescope}')

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
            request_timeout = time() + self._get_client_config().get('request_timeout', 2.01)

        try:
            res = await self.client.put_async(f'{address}',
                                              time_of_data=time_of_data,
                                              time_of_data_tolerance=time_of_data_tolerance,
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
            raise OcaboxError.from_response('PUT', address, res.error)
        try:
            ret = res.value.v
        except Exception as e:
            logger.error(f'Return value not exisit regardless status=True, when setting value to {address}: {e}')
            raise OcaboxServerError(f'Value error on PUT {address}: {res.error}') from e
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
            time_of_data_tolerance = self._get_client_config().get('time_of_data_tolerance',
                                                                   self._time_of_data_tolerance)
        if request_timeout is None:
            request_timeout = time() + self._get_client_config().get('request_timeout', 2.02)

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
            raise OcaboxError.from_response('GET', address, res.error)
        try:
            ret = res.value.v
        except Exception as e:
            logger.error(f'Return value not exisit regardless status=True when getting value from {address}: {e}')
            raise OcaboxServerError(f'Value error on GET {address}: {res.error}') from e

        return ret

    async def subscribe_async(self, address: str,
                              time_of_data_tolerance: float | None = None,
                              delay: float | None = None,
                              name: str | None = None,
                              max_missed_msg: int | None = None,
                              parameters_dict: dict = None,
                              callback_method=None,
                              async_callback_method=None,
                              ignore_errors: bool = False,
                              error_policy: ErrorPolicy | None = None,
                              policy: ErrorPolicy | str | None = None,
                              max_data_age: float | None = None,
                              ):
        """Subscribes to specified address
        Blocks!
        @param address: Address of requested value
        @param time_of_data_tolerance:
        @param delay: minimum delay between pulling updated values
        @param parameters_dict: additional parameters for get
        @param ignore_errors: deprecated; pass ``policy=ErrorPolicy.SERVICE``
            for the same effect on long-running daemons.
        @param error_policy: deprecated alias of ``policy``.
        @param max_data_age: T2 — data older than this is no longer an
            acceptable answer for this subscription (defaults to
            ``2 * time_of_data_tolerance`` when the policy declares a value
            axis; irrelevant otherwise).
        @param policy: per-call override of the observatory-wide policy
            (:class:`obcom.comunication.error_policy.ErrorPolicy` or a preset
            name). When neither ``policy`` nor ``error_policy`` is given, the
            subscription inherits ``Observatory(policy=…)`` — including its
            value_policy axis (a declaring policy rides in request_data and
            requires ocabox-server >= 2.5.2).
        """
        if policy is not None:
            if isinstance(policy, str):
                try:
                    policy = self.POLICY_PRESETS[policy.lower()]
                except KeyError:
                    raise ValueError(f"Unknown policy preset {policy!r}; "
                                     f"expected one of {sorted(self.POLICY_PRESETS)}")
            if not isinstance(policy, ErrorPolicy):
                raise ValueError(f"policy must be an ErrorPolicy or preset name, got {type(policy)}")
            error_policy = policy
        elif error_policy is not None:
            warnings.warn("'error_policy' is deprecated; use 'policy=' (per-call) or "
                          "Observatory(policy=…) (client-wide).",
                          DeprecationWarning, stacklevel=2)
        elif not ignore_errors:
            error_policy = self._policy

        if time_of_data_tolerance is None:
            time_of_data_tolerance = self._get_client_config().get('time_of_data_tolerance',
                                                                   self._time_of_data_tolerance)
        if max_data_age is None and self._max_data_age_explicit:
            # inherit the client-wide truth bound (the wire clamps T2 >= T1)
            max_data_age = self._max_data_age
        if delay is None:
            delay = self._get_client_config().get('delay', None)
        if name is None:
            name = f'Sub: {address}'
        if max_missed_msg is None:
            max_missed_msg = self._get_client_config().get('max_missed_msg', None)

        cq = await self.client.subscribe_with_callback(address,
                                                       time_of_data_tolerance=time_of_data_tolerance,
                                                       delay=delay,
                                                       parameters_dict=parameters_dict,
                                                       name=name,
                                                       max_missed_msg=max_missed_msg,
                                                       callback_method=callback_method,
                                                       async_callback_method=async_callback_method,
                                                       ignore_errors=ignore_errors,
                                                       error_policy=error_policy,
                                                       max_data_age=max_data_age,
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
            async with asyncio.timeout(time_to_close):
                await cq.stop_and_wait()  # the task should finish in less than 0.5 seconds
        except TimeoutError:
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
                                  parameters_dict: dict = None,
                                  ignore_errors: bool = False):
        """Subscribes to specified address
        Blocks!
        @param address: Address of requested value
        @param time_of_data_tolerance:
        @param delay: minimum delay between pulling updated values
        @param parameters_dict: additional parameters for get
        """

        if time_of_data_tolerance is None:
            time_of_data_tolerance = self._get_client_config().get('time_of_data_tolerance',
                                                                   self._time_of_data_tolerance)
        if delay is None:
            delay = self._get_client_config().get('delay', None)
        if name is None:
            name = f'Sub: {address}'
        if max_missed_msg is None:
            max_missed_msg = self._get_client_config().get('max_missed_msg', None)

        cq = await self.client.subscribe(address,
                                         time_of_data_tolerance=time_of_data_tolerance,
                                         delay=delay,
                                         parameters_dict=parameters_dict,
                                         name=name,
                                         max_missed_msg=max_missed_msg,
                                         ignore_errors=ignore_errors
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
        # raise CriticalErrorAbort(f'Synchronous get from `TelescopeComponent` and derived classes is not supported by '
        #                          f'ocabox yet. Use `async_get` for {address} instead.')
        #
        # oldloop = asyncio.get_event_loop()
        # try:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        #     future = asyncio.run(self.get_async(address,
        #                                         time_of_data=time_of_data,
        #                                         time_of_data_tolerance=time_of_data_tolerance,
        #                                         request_timeout=request_timeout,
        #                                         parameters_dict=parameters_dict))
        #     ret = future.result()
        #
        #     # loop = asyncio.get_event_loop()
        #     # tsk  = loop.create_task(self.get_async(address,
        #     #                                   time_of_data=time_of_data,
        #     #                                   time_of_data_tolerance=time_of_data_tolerance,
        #     #                                   request_timeout=request_timeout,
        #     #                                   parameters_dict=parameters_dict)
        #     #                    )
        # except Exception as e:
        #     logger.error(f'Error getting value from {address}: {e}')
        #     raise e
        # finally:
        #     asyncio.set_event_loop(oldloop)
        # return ret

    async def reload_server_config(self) -> bool:
        """ On the server side, the configuration is reloaded from the config file and sends new configuration to NATS

        This is server admin operation. It is not intended to be used by clients. It does not read the
        client configuration from the NATS server.

        To reload the client configuration from the NATS server, use the `load_client_cfg` method.
        """
        return await self.client.server_reload_nats_config()
