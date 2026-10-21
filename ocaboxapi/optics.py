"""Optical path of a telescope, served by the optics service through TIC.

TIC reaches the ocabox-tcs ``optics`` service with its NATS service driver, so its state reads,
subscribes and errors like any device (addresses ``<tel>.optics.<detector>.<item>`` and
``<tel>.optics.self.<item>``):

- :class:`OpticalDetector` — one instrument: what it ``sees`` now, the verdict of each of its
  ``functions`` (object, dark, flat, …), and ``aput_setpath(function)`` to switch the light path.
- :class:`OpticsState` — every selector axis (position, why it is unknown, its label), the
  positions people vouch for (``declared``), the detectors whose path must not change (``busy``),
  and the last path change (``operation``: moving → done | failed); ``aput_declare`` to vouch for
  what no reading proves (a shutter opened by hand while its sensor reports an error).

Subscriptions hand the callback what TIC delivered, the obcom ``Value`` — ``callback(value)``, a
coroutine function too (awaited by the subscription in delivery order). ``value.v`` is the document;
``None`` is a verdict, not a blank: ``value.tags['reason']`` says why there is no truthful one — the
code of the Staleness Contract's rich None (older than the subscription's ``max_data_age``, with
``last_good``/``last_good_ts`` when one was ever seen) or of the error TIC answered with, its text in
``tags['message']`` (TIC unreachable, the optics service silent, …). Under a policy without the
value axis (``value_policy`` other than NONE, e.g. INTERACTIVE) a server's None stops the
subscription: it is the last delivery. The component's cache follows the deliveries, so the sync
properties and ``value_tags()`` agree with what the callback saw; the subscriptions are the
component's own, so ``Telescope.unsubscribe_all_component`` ends them.

``aput_setpath`` returns as soon as the service accepts (``{'accepted': True, 'moves': {...}}``)
and the switch runs like a slew: follow ``operation``. A refusal raises the server error with the
service's code — 4007 no such detector or function, 4008 (``CameraBusy``-like, temporary) a busy
detector's path or another switch in progress, 4009 (``OcaboxDeviceError``) a manual move needed or
the light unavailable; the message says which.
"""
from __future__ import annotations

import inspect
import logging
import time
from typing import Awaitable, Callable

from obcom.data_colection.value import Value
from obcom.data_colection.value_call import ValueResponse
from ocaboxapi.component import Component
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


#: what a subscription hands its callback: the delivered ``Value`` (``v`` None with ``tags['reason']``
#: when TIC has no truthful one)
ValueCallback = Callable[[Value], None | Awaitable[None]]


class _OpticsComponent(TelescopeComponent):
    """A part of the optics service as TIC serves it: subscriptions deliver values, not events, and
    a ``None`` is a verdict — its tags say why."""

    async def _asubscribe_value(self, item: str, callback: ValueCallback, time_of_data_tolerance: float | None,
                                max_data_age: float | None):
        """Subscribe to ``item`` and hand ``callback`` every delivered value; the cycle query. A
        coroutine function is awaited by the subscription's callback runner — in delivery order, its
        failure logged — never launched as a task of its own."""
        if inspect.iscoroutinefunction(callback):
            async def deliver(responses):
                await callback(self._delivered(item, responses[0]))
            how = {'async_callback_method': deliver}
        else:
            def deliver(responses):
                callback(self._delivered(item, responses[0]))
            how = {'callback_method': deliver}
        cq = await self.observatory.subscribe_async(f'{self.my_address()}.{item}', **how,
                                                    time_of_data_tolerance=time_of_data_tolerance, max_data_age=max_data_age)
        self.subscribed.append(Component.CQHolder(cq, item))
        return cq

    def _delivered(self, item: str, response: ValueResponse) -> Value:
        """The ``Value`` of one delivery. A value (a rich None too) also becomes the component's
        cached ``item``: the subscription is the freshness witness of that cache, so it must feed
        it. An error answer leaves the cache alone, as ``Component.subscribe`` does, and is told as
        a None with the error's code and text."""
        if response.status and response.value is not None:
            value = response.value
            setattr(self, f'_{item}_value_tags', dict(value.tags or {}))
            self.param.update(**{f'_{item}_value': value.v})
            return value
        error = response.error
        if error is None:
            return Value(None, time.time(), tags={'reason': None, 'message': 'no value in the answer'})
        return Value(None, time.time(), tags={'reason': error.code, 'message': error.message})


class OpticalDetector(_OpticsComponent):
    """The light path of one detector (``Telescope.get_optical_detector('camera')``)."""

    sees = OcaBoxParam(default=None, doc="What the detector sees now: list of {class, terminal, via}")
    functions = OcaBoxParam(default=None, doc="Verdict per declared function: {function: {kind, ...}}")

    async def aget_sees(self, time_of_data_tolerance: float | None = None) -> list[dict] | None:
        return await self.aget_value('sees', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_sees(self, callback: ValueCallback, time_of_data_tolerance: float | None = None,
                              max_data_age: float | None = None):
        return await self._asubscribe_value('sees', callback, time_of_data_tolerance, max_data_age)

    async def aget_functions(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('functions', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_functions(self, callback: ValueCallback, time_of_data_tolerance: float | None = None,
                                   max_data_age: float | None = None):
        return await self._asubscribe_value('functions', callback, time_of_data_tolerance, max_data_age)

    async def aput_setpath(self, function: str) -> dict:
        """Switch the light path so the detector can do ``function``; returns the accepted moves."""
        logger.info(f'{self.my_address()}: setpath {function}')
        return await self.aput_value('setpath', function=function)


class OpticsState(_OpticsComponent):
    """The telescope-wide state of the optics service (``Telescope.get_optics()``)."""

    selectors = OcaBoxParam(default=None, doc="Every state axis, selectors and sources (sky, lamps): {key: {position, origin, moving, cause, by, label}}")
    declared = OcaBoxParam(default=None, doc="Positions people vouch for: {key: {position, by, at}}")
    busy = OcaBoxParam(default=None, doc="Detectors whose light path must not change: {detector: why}")
    operation = OcaBoxParam(default=None, doc="Last path change: {state, detector, function, moves, caller, message}")

    async def aget_selectors(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('selectors', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_selectors(self, callback: ValueCallback, time_of_data_tolerance: float | None = None,
                                   max_data_age: float | None = None):
        return await self._asubscribe_value('selectors', callback, time_of_data_tolerance, max_data_age)

    async def aget_declared(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('declared', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_declared(self, callback: ValueCallback, time_of_data_tolerance: float | None = None,
                                  max_data_age: float | None = None):
        return await self._asubscribe_value('declared', callback, time_of_data_tolerance, max_data_age)

    async def aput_declare(self, key: str, position: str | None) -> dict:
        """Vouch for selector ``key`` (``dome``) being at ``position`` when no reading can prove it;
        ``None`` withdraws. Refused (4009) while a reading proves the axis; withdrawn by the service
        as soon as one does, and after the night. Returns the live declarations."""
        logger.info(f'{self.my_address()}: declare {key} {position}')
        return await self.aput_value('declare', key=key, position=position)

    async def aget_busy(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('busy', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_busy(self, callback: ValueCallback, time_of_data_tolerance: float | None = None,
                              max_data_age: float | None = None):
        return await self._asubscribe_value('busy', callback, time_of_data_tolerance, max_data_age)

    async def aget_operation(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('operation', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_operation(self, callback: ValueCallback, time_of_data_tolerance: float | None = None,
                                   max_data_age: float | None = None):
        return await self._asubscribe_value('operation', callback, time_of_data_tolerance, max_data_age)
