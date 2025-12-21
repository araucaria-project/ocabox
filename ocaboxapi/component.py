from __future__ import annotations

import asyncio
import dataclasses
import logging
import time
from typing import Any, List

import param
from obcom.comunication.cycle_query import BaseCycleQuery

from obcom.data_colection.value_call import ValueResponse
from ocaboxapi import Observatory
from ocaboxapi.exceptions import OcaboxServerError

logger = logging.getLogger('component')

param.parameterized.async_executor = lambda f: asyncio.create_task(f())


class OcaBoxParam(param.Dynamic):
    pass


class Component(param.Parameterized):
    id = param.String()
    observatory: Observatory = param.ClassSelector(class_=Observatory)

    @dataclasses.dataclass
    class CQHolder:
        cq: BaseCycleQuery
        id: str

    def __init__(self, **params):
        self.request_special_permission = False
        super().__init__(**params)
        self.subscribed: List[Component.CQHolder] = []
        self._watchers: list = []
        self._initialize()

    async def aget_value(self, param_name, request_timeout: float = None, **parameters_dict):
        """Asynchronously get value, value will be pulled form OCABOX only if needed"""
        if self._needs_refresh(param_name):
            try:
                new_val = await self._apull_value(param_name,
                                                  request_timeout=request_timeout,
                                                  parameters_dict=parameters_dict)
                setattr(self, f'_{param_name}_value', new_val)
                return new_val
            except (OcaboxServerError, CommunicationTimeoutError, CommunicationRuntimeError, OcaboxAccessDenied)  as e:
                logger.warning(f'Refresh failed for {self.id}.{param_name} ({e}), serving stale data to prevent crash.')
                # Cheat that the value is newer
                setattr(self, f'_{param_name}_timestamp', time.time())


        return getattr(self, f'_{param_name}_value')

    async def aput_value(self, param_name, **kwargs):
        """Asynchronously put value, value will be pushed to OCABOX"""
        try:
            return await self._aput_value(param_name, **kwargs)
        except OcaboxServerError as e:
            logger.info(f'Error while putting value {kwargs} for {param_name}: {e}')
            raise

    def watch(self, param_names, callback, queued=False):
        """ Add watcher for local value(s) change, callback will be called with Event as argument

        You may specify multiple parameters to watch.
        Callback can be coroutine, in that case it will be executed in asyncio loop.
        `watch` does not subscribe for value change on OCABOX, it just watches local value change. """
        logger.debug(f'Setting watcher on {param_names}: {callback}')
        watcher = self.param.watch(callback, param_names, queued=queued)
        self._watchers.append(watcher)
        return watcher

    def unwatch(self, watcher):
        """ Remove watcher

        `watcher` is returned by `watch` method."""
        self.param.unwatch(watcher)

    def unwatch_all(self):
        """ Remove all watcher

        `watcher` is returned by `watch` method."""
        for w in self._watchers:
            self.param.unwatch(w)
        self._watchers = []

    def my_address(self):
        """ Return address of this component """
        return f'{self.id}'

    async def subscribe(self, param_name, callback=None, time_of_data_tolerance: float | None = None,
                        **parameters_dict):
        """ Add watcher for value change, callback will be called with Event as argument

        Callback can be cooroutine, in that case it will be executed in asyncio loop.
        `subscribe` subscribes for value changes on OCABOX.
        If callback = None, then subscription still be made, and will affect other watchers,
        user can add watchers anytime using `watch` method. """
        address = f'{self.my_address()}.{param_name}'

        def sub_callback(resps: List[ValueResponse]):
            logger.debug(f'Sub callback for {address}: {resps}')
            try:
                if resps[0].status:
                    v = resps[0].value.v
                    self.param.update(**{f'_{param_name}_value': v})
                else:
                    logger.error(f'Error in {param_name} ({resps[0].address}) subscription {resps[0].error}')
            except Exception as e:
                logger.error(f'Error in callback for {address} with resp: {resps}: {e}')
                return

        # === FIX: Watcher first ===
        watcher = None
        if callback is not None:
            watcher = self.watch(param_names=param_name, callback=callback)
        # ========================================

        cq = await self.observatory.subscribe_async(address,
                                                    callback_method=sub_callback,
                                                    time_of_data_tolerance=time_of_data_tolerance,
                                                    parameters_dict=parameters_dict
                                                    )

        self.subscribed.append(Component.CQHolder(cq, param_name))
        return cq, watcher

    def unsubscribe(self, cq):
        self.observatory.unsubscribe(cq)
        to_remove = None
        for cq_holder in self.subscribed:
            if cq == cq_holder.cq:
                to_remove = cq_holder
                break
        if to_remove is not None:
            self.subscribed.remove(to_remove)

    def unsubscribe_all(self):
        for cq_holder in self.subscribed:
            self.observatory.unsubscribe(cq_holder.cq)
        self.subscribed = []

    def reset_params_values(self):
        to_reset = [n for n, p in self.param.objects(instance='existing').items() if isinstance(p, OcaBoxParam)]
        for n in to_reset:
            setattr(self, f'_{n}_value', None)

    def __del__(self):
        self.unsubscribe_all()

    def _initialize(self):
        to_connect = [n for n, p in self.param.objects(instance='existing').items() if isinstance(p, OcaBoxParam)]
        for n in to_connect:
            self._connect_variables(n)

    def _connect_variables(self, param_name):
        logger.debug(f'Connecting {param_name} to {self.id}')
        # parameter = self.param.values()params()[param_name]
        self.param.add_parameter(f'_{param_name}_value', param.Parameter(None, allow_None=True))
        self.param.add_parameter(f'_{param_name}_timestamp', param.Number(0.0))
        with param.discard_events(self):
            self.param.update(**{param_name: lambda: self._ensure_value(param_name)})
        self.param.watch(lambda event: self._watcher(event, param_name), f'_{param_name}_value')

    def _watcher(self, event, param_name):
        setattr(self, f'_{param_name}_timestamp', time.time())
        self.param.trigger(param_name)

    def _needs_refresh(self, param_name):
        time_of_data_tolerance = self.observatory.time_of_data_tolerance
        return (getattr(self, f'_{param_name}_timestamp') + time_of_data_tolerance < time.time()
                or getattr(self, f'_{param_name}_value') is None)

    def _ensure_value(self, param_name):
        # With the lack of synchronous `get` from ClientAPI, we never lazy refresh
        # values get synchronolusly.
        # TODO: Add refresh, if when synchronoous get is implemented
        # if (self._needs_refresh(param_name)):
        # noinspection PyUnreachableCode
        if False:
            setattr(self, f'_{param_name}_value', self._pull_value(param_name))
        return getattr(self, f'_{param_name}_value')

    async def _apull_value(self, param_name, request_timeout: float | None = None, parameters_dict: dict | None = None):
        return await self._get_async(param_name, request_timeout=request_timeout, parameters_dict=parameters_dict)

    def _pull_value(self, param_name):
        return self._get(param_name)

    async def _aput_value(self, param_name, **kwargs):
        return await self._put_async(param_name, parameters_dict=kwargs)

    def _put_value(self, param_name, value):
        self._put(param_name, value)

    async def _put_async(self, param_name: str,
                         time_of_data: float | None = None,
                         time_of_data_tolerance: float | None = None,
                         request_timeout: float | None = None,
                         parameters_dict: dict | None = None) -> Any:
        address = f'{self.my_address()}.{param_name}'
        logger.debug(f'Awaiting for put_async {address}')
        if self.request_special_permission:
            if parameters_dict is None:
                parameters_dict = {}
            parameters_dict['request_special_permission_param'] = True
        ret = await self.observatory.put_async(address,
                                               time_of_data=time_of_data,
                                               time_of_data_tolerance=time_of_data_tolerance,
                                               request_timeout=request_timeout,
                                               parameters_dict=parameters_dict)
        logger.debug(f'Got put_async {address}, response: {repr(ret)[:20]}')
        return ret

    async def _get_async(self, param_name: str,
                         time_of_data: float | None = None,
                         time_of_data_tolerance: float | None = None,
                         request_timeout: float | None = None,
                         parameters_dict: dict | None = None) -> Any:
        address = f'{self.my_address()}.{param_name}'
        logger.debug(f'Awaiting for get_async {address}')
        ret = await self.observatory.get_async(address,
                                               time_of_data=time_of_data,
                                               time_of_data_tolerance=time_of_data_tolerance,
                                               request_timeout=request_timeout,
                                               parameters_dict=parameters_dict)
        logger.debug(f'Got get_async {address}, response: {repr(ret)[:20]}')
        return ret

    def _get(self, param_name: str,
             time_of_data: float | None = None,
             time_of_data_tolerance: float | None = None,
             request_timeout: float | None = None,
             parameters_dict: dict | None = None) -> Any:
        address = f'{self.my_address()}.{param_name}'
        logger.debug(f'Awaiting for get {address}')
        ret = self.observatory.get(address,
                                   time_of_data=time_of_data,
                                   time_of_data_tolerance=time_of_data_tolerance,
                                   request_timeout=request_timeout,
                                   parameters_dict=parameters_dict)
        logger.debug(f'Got get {address}, response: {repr(ret)[:20]}')
        return ret

    def __str__(self):
        return f'{self.id}'
