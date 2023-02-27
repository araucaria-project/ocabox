from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, List, Callable

import param

from ob.data_colection.value_call import ValueResponse
from ocaboxapi.abstelescope import AbstractTelescope
from ocaboxapi.exceptions import OcaboxServerError

logger = logging.getLogger('tel component')

param.parameterized.async_executor = lambda f: asyncio.create_task(f())


class OcaBoxParam(param.Dynamic):
    pass


# noinspection PyUnresolvedReferences
class TelescopeComponent(param.Parameterized):
    id = param.String()
    telescope: 'Telescope' = param.ClassSelector(class_=AbstractTelescope)
    connected = OcaBoxParam(default=False, doc="Is component connected")
    name = OcaBoxParam(default='', doc="Component name")
    description = OcaBoxParam(default='', doc="Component description")

    def __init__(self, **params):
        super().__init__(**params)
        self.subscribed = []
        self._initialize()

    async def asubscribe_connected(self, callback: Callable | None = None,
                                   time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing connected from {self.tel_addr}')
        await self.subscribe('connected', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_connected(self) -> bool:
        logger.debug(f'Getting  connected from {self.tel_addr}')
        ret = await self.aget_value('connected')
        return ret

    async def aput_connect(self, connect: bool):
        logger.debug(f'Putting  connect = {connect} to {self.tel_addr}')
        await self.aput_value('connected', connected=connect)

    async def asubscribe_name(self, callback: Callable | None = None,
                              time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing name from {self.tel_addr}')
        await self.subscribe('name', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_name(self) -> str:
        logger.debug(f'Getting  name from {self.tel_addr}')
        ret = await self.aget_value('name')
        return ret

    async def asubscribe_description(self, callback: Callable | None = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing description from {self.tel_addr}')
        await self.subscribe('description', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_description(self) -> str:
        logger.debug(f'Getting  description from {self.tel_addr}')
        ret = await self.aget_value('description')
        return ret

    @property
    def tel_addr(self) -> str:
        return self.telescope.tel_addr

    async def aget_value(self, param_name):
        """Asynchronously get value, value will be pulled form OCABOX only if needed"""
        if self._needs_refresh(param_name):
            try:
                new_val = await self._apull_value(param_name)
            except OcaboxServerError as e:
                logger.info(f'Error while pulling value for {param_name}: {e}')
                new_val = None
            setattr(self, f'_{param_name}_value', new_val)
        return getattr(self, f'_{param_name}_value')

    async def aput_value(self, param_name, **kwargs):
        """Asynchronously put value, value will be pushed to OCABOX"""
        try:
            await self._aput_value(param_name, **kwargs)
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
        return watcher

    def unwatch(self, watcher):
        """ Remove watcher

        `watcher` is returned by `watch` method."""
        self.param.unwatch(watcher)

    async def subscribe(self, param_name, callback=None, time_of_data_tolerance: float | None = None):
        """ Add watcher for value change, callback will be called with Event as argument

        Callback can be cooroutine, in that case it will be executed in asyncio loop.
        `subscribe` subscribes for value changes on OCABOX.
        If callback = None, then subscription still be made, and will affect other watchers,
        user can add watchers anytime using `watch` method. """
        address = f'{self.tel_addr}.{self.id}.{param_name}'

        def sub_callback(resps: List[ValueResponse]):
            logger.debug(f'Sub callback for {address}: {resps}')
            try:
                if resps[0].status:
                    v = resps[0].value.v
                    self.param.set_param(f'_{param_name}_value', v)
            except Exception as e:
                logger.error(f'Error in callback for {address} with resp: {resps}: {e}')
                return

        cq = await self.telescope.observatory.subscribe_async(address,
                                                              callback_method=sub_callback,
                                                              time_of_data_tolerance=time_of_data_tolerance
                                                              )

        self.subscribed.append(cq)
        if callback is not None:
            # self.watch(param_name=param_name, callback=lambda event: callback(getattr(event.obj, param_name)))
            watcher = self.watch(param_names=param_name, callback=callback)
        else:
            watcher = None
        return cq, watcher

    def unsubscribe(self, cq):
        self.telescope.observatory.unsubscribe(cq)
        self.subscribed.remove(cq)

    def unsubscribe_all(self):
        for cq in self.subscribed:
            self.telescope.observatory.unsubscribe(cq)
        self.subscribed = []

    def __del__(self):
        self.unsubscribe_all()

    def _initialize(self):
        for n, p in self.param.params().items():
            if isinstance(p, OcaBoxParam):
                self._connect(n)

    def _connect(self, param_name):
        logger.debug(f'Connecting {param_name} to {self.id}')
        # parameter = self.param.params()[param_name]
        self.param.add_parameter(f'_{param_name}_value', param.Parameter(None, allow_None=True))
        self.param.add_parameter(f'_{param_name}_timestamp', param.Number(0.0))
        with param.discard_events(self):
            self.param.set_param(param_name, lambda: self._ensure_value(param_name))
        self.param.watch(lambda event: self._watcher(event, param_name), f'_{param_name}_value')

    def _watcher(self, event, param_name):
        setattr(self, f'_{param_name}_timestamp', time.time())
        self.param.trigger(param_name)

    def _needs_refresh(self, param_name):
        time_of_data_tolerance = self.telescope.observatory.time_of_data_tolerance
        return (getattr(self, f'_{param_name}_timestamp') + time_of_data_tolerance < time.time()
                or getattr(self, f'_{param_name}_value') is None)

    def _ensure_value(self, param_name):
        ## With the lack of synchronous `get` from ClientAPI, we never lazy refresh
        ## values get synchronolusly.
        ## TODO: Add refresh, if when synchronoous get is implemented
        # if (self._needs_refresh(param_name)):
        if False:
            setattr(self, f'_{param_name}_value', self._pull_value(param_name))
        return getattr(self, f'_{param_name}_value')

    async def _apull_value(self, param_name):
        return await self._get_async(param_name)

    def _pull_value(self, param_name):
        return self._get(param_name)

    async def _aput_value(self, param_name, **kwargs):
        await self._put_async(param_name, parameters_dict=kwargs)

    def _put_value(self, param_name, value):
        self._put(param_name, value)

    async def _put_async(self, param_name: str,
                         time_of_data: float | None = None,
                         time_of_data_tolerance: float | None = None,
                         request_timeout: float | None = None,
                         parameters_dict: dict | None = None) -> Any:
        address = f'{self.tel_addr}.{self.id}.{param_name}'
        logger.debug(f'Awaiting for put_async {address}')
        ret = await self.telescope.observatory.put_async(address,
                                                         time_of_data=time_of_data,
                                                         time_of_data_tolerance=time_of_data_tolerance,
                                                         request_timeout=request_timeout,
                                                         parameters_dict=parameters_dict)
        logger.debug(f'Got put_async {address}, response: {ret}')
        return ret

    async def _get_async(self, param_name: str,
                         time_of_data: float | None = None,
                         time_of_data_tolerance: float | None = None,
                         request_timeout: float | None = None,
                         parameters_dict: dict | None = None) -> Any:
        address = f'{self.tel_addr}.{self.id}.{param_name}'
        logger.debug(f'Awaiting for get_async {address}')
        ret = await self.telescope.observatory.get_async(address,
                                                         time_of_data=time_of_data,
                                                         time_of_data_tolerance=time_of_data_tolerance,
                                                         request_timeout=request_timeout,
                                                         parameters_dict=parameters_dict)
        logger.debug(f'Got get_async {address}, response: {ret}')
        return ret

    def _get(self, param_name: str,
             time_of_data: float | None = None,
             time_of_data_tolerance: float | None = None,
             request_timeout: float | None = None,
             parameters_dict: dict | None = None) -> Any:
        address = f'{self.tel_addr}.{self.id}.{param_name}'
        logger.debug(f'Awaiting for get {address}')
        ret = self.telescope.observatory.get(address,
                                             time_of_data=time_of_data,
                                             time_of_data_tolerance=time_of_data_tolerance,
                                             request_timeout=request_timeout,
                                             parameters_dict=parameters_dict)
        logger.debug(f'Got get {address}, response: {ret}')
        return ret


class TelescopeComponentOld():

    def __init__(self, id: str, telescope: "AbstractTelescope") -> None:
        self.id = id
        self.telescope: "AbstractTelescope" = telescope
        self.subscriptions = []
        super().__init__()

    @property
    def tel_addr(self) -> str:
        return self.telescope.tel_addr

    async def get_async(self, path: str,
                        time_of_data: float | None = None,
                        time_of_data_tolerance: float | None = None,
                        request_timeout: float | None = None,
                        parameters_dict: dict | None = None) -> Any:
        address = f'{self.tel_addr}.{self.id}.{path}'
        logger.debug(f'Awaiting for get_async {address}')
        ret = await self.telescope.observatory.get_async(address,
                                                         time_of_data=time_of_data,
                                                         time_of_data_tolerance=time_of_data_tolerance,
                                                         request_timeout=request_timeout,
                                                         parameters_dict=parameters_dict)
        logger.debug(f'Got get_async {address}, response: {ret}')
        return ret
