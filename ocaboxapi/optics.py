"""Optical path of a telescope, served by the optics service through TIC.

TIC reaches the ocabox-tcs ``optics`` service with its NATS service driver, so its state reads,
subscribes and errors like any device (addresses ``<tel>.optics.<detector>.<item>`` and
``<tel>.optics.self.<item>``):

- :class:`OpticalDetector` — one instrument: what it ``sees`` now, the verdict of each of its
  ``functions`` (object, dark, flat, …), and ``aput_setpath(function)`` to switch the light path.
- :class:`OpticsState` — every selector axis (position, why it is unknown, its label), the
  positions people vouch for (``declared``), the detectors whose path must not change (``busy``),
  and the last path change (``operation``: awaiting_confirmation → moving → done | failed, or
  rejected | expired | superseded); ``aput_declare`` to vouch for what no reading proves (a shutter
  opened by hand while its sensor reports an error); ``aput_confirm``/``aput_reject``/``aput_abort``
  for a change that waits for a person (optics service ≥ 1.7).

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

Some moves wait for a person (the telescope and the dome to the flat screen; the covers by day): the
verdict names them in ``confirm``, ``aput_setpath`` answers ``awaiting_confirmation`` with the
``operation`` id, what will move in words (``says``) and ``expires_at``, and nothing moves until
``aput_confirm(operation)``. For light still to come (the sky at dusk) the answer carries ``awaits``
and the moves prepare the path for it.
"""
from __future__ import annotations

import inspect
import logging
import time
from typing import Awaitable, Callable

from obcom.data_colection.value import Value
from obcom.data_colection.value_call import ValueResponse
from obcom.optics import component_label, station
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
    """One detector of the telescope (``Telescope.get_optical_detector('camera')``, every one:
    ``Telescope.get_detectors()``): what the configuration says of it — its ``config``, ``kind``,
    ``flags``, ``function_names``, the device that drives it, the parts in front of it
    (:meth:`upstream`) and the detectors selected with it (:attr:`station`) — and its light path as
    the optics service serves it (``sees``, ``functions`` verdicts, ``aput_setpath``)."""

    sees = OcaBoxParam(default=None, doc="What the detector sees now: list of {class, terminal, via}")
    functions = OcaBoxParam(default=None, doc="Verdict per declared function: {function: {kind, ...}}")

    @property
    def component_name(self) -> str:
        """The detector's component name (``camera``, also its ``name``); its address is ``<tel>.optics.camera``."""
        return self.id.partition('.')[2]

    @property
    def label(self) -> str:
        """What people call it (``display.label``: "BESO guider"), else its name."""
        graph = self.telescope.optical_graph
        return component_label(graph, self.name) if graph is not None and self.name in graph.nodes else self.name

    @property
    def function_names(self) -> tuple[str, ...]:
        """The functions it performs (``paths:``: object, dark, arc …); none for a guider."""
        return tuple(self.config.get('paths') or ())

    @property
    def device(self):
        """The device that drives it (``Camera('camera')``); ``None`` when TIC serves none for its kind
        (BESO is driven by its own server)."""
        try:
            return self.telescope.get_component(self.name)
        except LookupError:
            return None

    def upstream(self, kind: str) -> list:
        """The devices of ``kind`` light can reach it through, nearest first, by configuration — the
        same at every M3 position: ``upstream('filterwheel')`` is its filter wheel, ``upstream('rotator')``
        its rotator (shared with its guider); empty when it has none."""
        graph = self.telescope.optical_graph
        if graph is None or self.name not in graph.nodes:
            return []
        return [self.telescope.get_component(name) for name in graph.upstream_of(self.name, kind)]

    @property
    def station(self) -> list[OpticalDetector]:
        """The detectors the routing selectors (M3) select together with it, itself included, in
        configuration order: the camera and its guider."""
        graph = self.telescope.optical_graph
        if graph is None or self.name not in graph.nodes:
            return [self]
        return [self.telescope.get_optical_detector(name) for name in station(graph, self.name)]

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

    async def aput_confirm(self, operation: str) -> dict:
        """A person confirms the light-path change ``operation`` that waits for one (the telescope and
        the dome to the flat screen; the covers by day) — exactly as ``operation`` shows it. Refused
        (4008) when the state changed since it was asked: ask again; 4007 when it does not wait."""
        logger.info(f'{self.my_address()}: confirm {operation}')
        return await self.aput_value('confirm', operation=operation)

    async def aput_reject(self, operation: str, reason: str | None = None) -> dict:
        """A person turns the waiting change ``operation`` down; nothing moves."""
        logger.info(f'{self.my_address()}: reject {operation}' + (f' ({reason})' if reason else ''))
        return await self.aput_value('reject', operation=operation, reason=reason)

    async def aput_abort(self, operation: str) -> dict:
        """Stop ``operation``: a waiting one is turned down, a running one stops the telescope and the
        dome where they are."""
        logger.info(f'{self.my_address()}: abort {operation}')
        return await self.aput_value('abort', operation=operation)

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
