from __future__ import annotations

import asyncio
import dataclasses
import logging
import time
from typing import Any, List

import param
from obcom.comunication.cycle_query import BaseCycleQuery

from obcom.data_colection.value_call import ValueResponse
from obcom.comunication.error_policy import ValuePolicy

from ocaboxapi import Observatory
from ocaboxapi.exceptions import OcaboxError, OcaboxStaleValueError

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
        # param names whose last refresh failed — log loudly only on the
        # transition into (and out of) the failed state, not per repaint
        self._failed_reads: set = set()
        self._initialize()

    async def aget_value(self, param_name, request_timeout: float = None,
                         time_of_data_tolerance: float = None,
                         value_policy: ValuePolicy | str | None = None,
                         max_data_age: float = None,
                         **parameters_dict):
        """Asynchronously get value, value will be pulled form OCABOX only if needed

        Temporal model (Staleness Contract): ``time_of_data_tolerance`` is T1 —
        the preferred freshness (a fresher cached value is served without I/O;
        an older one triggers a refresh; the TIC default is 60 s — pass an
        explicit tolerance when observing changing state). ``max_data_age`` is
        T2 — the truth bound (default ``2 * T1``): when a refresh FAILS, a
        cached value younger than T2 is still an acceptable answer and is
        served regardless of policy; only past T2 does the truth axis decide:
        ``RAISE`` propagates the exception (the honest default); ``NONE``
        returns ``None``; ``LAST_GOOD`` keeps serving the aging value — for
        bare-value callers that prefer old data over no data (no timestamp
        cheat: every read re-asks the server, whose negative cache absorbs
        the hammering).
        """
        if self._needs_refresh(param_name, time_of_data_tolerance):
            try:
                new_val = await self._apull_value(param_name,
                                                  request_timeout=request_timeout,
                                                  time_of_data_tolerance=time_of_data_tolerance,
                                                  parameters_dict=parameters_dict)
                setattr(self, f'_{param_name}_value', new_val)
                # Stamp explicitly: the param watcher stamps only on CHANGE
                # (onlychanged=True), so a successful refresh returning the
                # same value would otherwise look stale forever.
                setattr(self, f'_{param_name}_timestamp', time.time())
                if param_name in self._failed_reads:
                    self._failed_reads.discard(param_name)
                    logger.warning(f'{self.id}.{param_name}: refresh recovered.')
                return new_val
            except Exception as e:
                first_failure = param_name not in self._failed_reads
                self._failed_reads.add(param_name)
                log = logger.warning if first_failure else logger.debug
                cached = getattr(self, f'_{param_name}_value')
                age = time.time() - getattr(self, f'_{param_name}_timestamp')
                max_age = self._effective_max_age(time_of_data_tolerance, max_data_age)
                if cached is not None and age <= max_age:
                    # (T1, T2] repair window: the cached value is still the
                    # truth — mask the failure, whatever the policy.
                    log(f'Refresh failed for {self.id}.{param_name} ({e}), serving the '
                        f'{age:.1f}s-old value (still within max_data_age={max_age}s).')
                    return cached
                vp = ValuePolicy(value_policy) if value_policy is not None \
                    else self.observatory.value_policy
                if vp is ValuePolicy.RAISE:
                    raise
                if vp is ValuePolicy.NONE:
                    log(f'Refresh failed for {self.id}.{param_name} ({e}) and the cached value '
                        f'is past max_data_age ({max_age}s) — returning None (value_policy NONE).')
                    return None
                log(f'Refresh failed for {self.id}.{param_name} ({e}), '
                    f'serving stale data (value_policy LAST_GOOD).')

        return getattr(self, f'_{param_name}_value')

    def _effective_max_age(self, time_of_data_tolerance: float | None,
                           max_data_age: float | None) -> float:
        """T2 for this read: explicit per-call > 2x the per-call T1 > observatory T2.

        The T2 >= T1 invariant is preserved (same clamp as the Observatory
        constructor and the wire): a T2 below the refresh threshold would
        create an age window (T2, T1) served from cache without any check.
        """
        t1 = (time_of_data_tolerance if time_of_data_tolerance is not None
              else self.observatory.time_of_data_tolerance)
        if max_data_age is not None:
            return max(float(max_data_age), t1)
        if time_of_data_tolerance is not None:
            return 2 * time_of_data_tolerance
        return self.observatory.max_data_age

    async def aput_value(self, param_name, **kwargs):
        """Asynchronously put value, value will be pushed to OCABOX"""
        try:
            return await self._aput_value(param_name, **kwargs)
        except OcaboxError as e:
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

    def value_tags(self, param_name) -> dict:
        """Tags of the last subscription-delivered value for ``param_name``.

        For a rich stale-None (Staleness Contract) this carries ``reason``,
        ``last_good`` and ``last_good_ts`` — what a display needs to grey out
        the last known value instead of showing a bare blank."""
        return getattr(self, f'_{param_name}_value_tags', {})

    async def subscribe(self, param_name, callback=None, time_of_data_tolerance: float | None = None,
                        max_data_age: float | None = None,
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
                    # if param_name == 'domefansrunning':
                        # logger.error(f'========DOME FANS QUERY CALLBACK old_val: '
                        #              f'{self.__getattribute__("_domefansrunning_value")} at '
                        #              f'{self.__getattribute__("_domefansrunning_timestamp")}')
                    v = resps[0].value.v
                    setattr(self, f'_{param_name}_value_tags', dict(resps[0].value.tags or {}))
                    # if param_name == 'domefansrunning':
                        # logger.error(f'========DOME FANS QUERY CALLBACK incomming status: {resps[0].status}, error: {resps[0].error} at '
                        #              f'{resps[0].value.ts} [{resps[0].value.tags}]')
                        # logger.error(f'========DOME FANS QUERY CALLBACK incomming v: {v}: {resps[0].value.type} at '
                        #              f'{resps[0].value.ts} [{resps[0].value.tags}]')
                        # logger.error(f'========DOME FANS QUERY CALLBACK watchers: {[w.fn.__name__ for w in self.param.watchers[param_name]["value"]]}')
                    self.param.update(**{f'_{param_name}_value': v})
                    # if param_name == 'domefansrunning':
                        # logger.error(f'========DOME FANS QUERY CALLBACK new_val: '
                        #              f'{self.__getattribute__("_domefansrunning_value")} at '
                        #              f'{self.__getattribute__("_domefansrunning_timestamp")}')
                else:
                    logger.error(f'Error in {param_name} ({resps[0].address}) subscription {resps[0].error}')
            except Exception as e:
                logger.error(f'Error in callback for {address} with resp: {resps}: {e}')
                return

        # === FIX: Watcher first ===
        watcher = None
        if callback is not None:
            # if param_name == 'domefansrunning':
            #     try:
            #         logger.error(
            #             f'========DOME FANS QUERY SUBSC adding watchers before: {[w.fn.__name__ for w in self.param.watchers[param_name]["value"]]}')
            #     except KeyError:
            #         logger.error(
            #             f'========DOME FANS QUERY SUBSC adding watchers before: No watchers')
            watcher = self.watch(param_names=param_name, callback=callback)
        #     if param_name == 'domefansrunning':
        #         logger.error(
        #             f'========DOME FANS QUERY SUBSC adding watchers after: {[w.fn.__name__ for w in self.param.watchers[param_name]["value"]]}')
        # # ========================================

        # if param_name == 'domefansrunning':
        #     logger.error(
        #         f'========DOME FANS QUERY SUBSC subscribing before: {[s.cq for s in self.subscribed]}')
        cq = await self.observatory.subscribe_async(address,
                                                    callback_method=sub_callback,
                                                    time_of_data_tolerance=time_of_data_tolerance,
                                                    max_data_age=max_data_age,
                                                    parameters_dict=parameters_dict
                                                    )

        self.subscribed.append(Component.CQHolder(cq, param_name))
        # if param_name == 'domefansrunning':
        #     logger.error(
        #         f'========DOME FANS QUERY SUBSC subscribing after: {[s.cq for s in self.subscribed]}')
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
        # if param_name == 'domefansrunning':
        #     logger.error(f'========DOME FANS PARAM connecting variables')

        logger.debug(f'Connecting {param_name} to {self.id}')
        # parameter = self.param.values()params()[param_name]
        self.param.add_parameter(f'_{param_name}_value', param.Parameter(None, allow_None=True))
        self.param.add_parameter(f'_{param_name}_timestamp', param.Number(0.0))
        with param.discard_events(self):
            self.param.update(**{param_name: lambda: self._ensure_value(param_name)})
        self.param.watch(lambda event: self._watcher(event, param_name), f'_{param_name}_value') #, onlychanged=False)

    def _watcher(self, event, param_name):
        setattr(self, f'_{param_name}_timestamp', time.time())
        self.param.trigger(param_name)

    def _needs_refresh(self, param_name, time_of_data_tolerance: float | None = None):
        if time_of_data_tolerance is None:
            time_of_data_tolerance = self.observatory.time_of_data_tolerance
        return (getattr(self, f'_{param_name}_timestamp') + time_of_data_tolerance < time.time()
                or getattr(self, f'_{param_name}_value') is None)

    def _ensure_value(self, param_name):
        # Sync property read: no I/O is possible here, so this is a pure age
        # judgment (Staleness Contract). A param with a live subscription is
        # exempt: the server + cycle-query already enforce the contract and
        # push a rich None when the truth expires — the local value IS the
        # contract-compliant view (its ts only moves on change, which says
        # nothing about freshness).
        value = getattr(self, f'_{param_name}_value')
        if value is None or self._is_subscribed(param_name):
            return value
        ts = getattr(self, f'_{param_name}_timestamp')
        if ts + self.observatory.max_data_age >= time.time():
            return value
        vp = self.observatory.value_policy
        if vp is ValuePolicy.LAST_GOOD:
            return value
        if vp is ValuePolicy.NONE:
            return None
        raise OcaboxStaleValueError(
            f'{self.id}.{param_name}: cached value is {time.time() - ts:.1f}s old, older than '
            f'max_data_age ({self.observatory.max_data_age}s). Use aget_{param_name}() '
            f'to refresh, subscribe, or declare a LAST_GOOD/NONE policy.')

    def _is_subscribed(self, param_name) -> bool:
        return any(holder.id == param_name for holder in self.subscribed)

    async def _apull_value(self, param_name, request_timeout: float | None = None,
                           time_of_data_tolerance: float | None = None,
                           parameters_dict: dict | None = None):
        return await self._get_async(param_name, request_timeout=request_timeout,
                                     time_of_data_tolerance=time_of_data_tolerance,
                                     parameters_dict=parameters_dict)

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
