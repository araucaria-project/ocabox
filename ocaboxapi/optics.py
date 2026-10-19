"""Optical path of a telescope, served by the optics service through TIC.

TIC reaches the ocabox-tcs ``optics`` service with its NATS service driver, so its state reads,
subscribes and errors like any device (addresses ``<tel>.optics.<detector>.<item>`` and
``<tel>.optics.self.<item>``):

- :class:`OpticalDetector` — one instrument: what it ``sees`` now, the verdict of each of its
  ``functions`` (object, dark, flat, …), and ``aput_setpath(function)`` to switch the light path.
- :class:`OpticsState` — the telescope's selectors, the detectors whose path must not change
  (``busy``), and the last path change (``operation``: moving → done | failed).

``aput_setpath`` returns as soon as the service accepts (``{'accepted': True, 'moves': {...}}``)
and the switch runs like a slew: follow ``operation``. A refusal raises the server error with the
service's code — 4007 no such detector or function, 4008 (``CameraBusy``-like, temporary) a busy
detector's path or another switch in progress, 4009 (``OcaboxDeviceError``) a manual move needed or
the light unavailable; the message says which.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class OpticalDetector(TelescopeComponent):
    """The light path of one detector (``Telescope.get_optical_detector('camera')``)."""

    sees = OcaBoxParam(default=None, doc="What the detector sees now: list of {class, terminal, via}")
    functions = OcaBoxParam(default=None, doc="Verdict per declared function: {function: {kind, ...}}")

    async def aget_sees(self, time_of_data_tolerance: float | None = None) -> list[dict] | None:
        return await self.aget_value('sees', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_sees(self, callback: Optional[Callable] = None, time_of_data_tolerance: float | None = None):
        return await self.subscribe('sees', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_functions(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('functions', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_functions(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        return await self.subscribe('functions', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_setpath(self, function: str) -> dict:
        """Switch the light path so the detector can do ``function``; returns the accepted moves."""
        logger.info(f'{self.my_address()}: setpath {function}')
        return await self.aput_value('setpath', function=function)


class OpticsState(TelescopeComponent):
    """The telescope-wide state of the optics service (``Telescope.get_optics()``)."""

    selectors = OcaBoxParam(default=None, doc="Proven selector positions: {key: {position, moving}}")
    busy = OcaBoxParam(default=None, doc="Detectors whose light path must not change: {detector: why}")
    operation = OcaBoxParam(default=None, doc="Last path change: {state, detector, function, moves, caller, message}")

    async def aget_selectors(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('selectors', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_selectors(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        return await self.subscribe('selectors', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_busy(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('busy', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_busy(self, callback: Optional[Callable] = None, time_of_data_tolerance: float | None = None):
        return await self.subscribe('busy', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_operation(self, time_of_data_tolerance: float | None = None) -> dict | None:
        return await self.aget_value('operation', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_operation(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        return await self.subscribe('operation', callback=callback, time_of_data_tolerance=time_of_data_tolerance)
