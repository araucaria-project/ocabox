from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class FlatScreen(TelescopeComponent):
    """Flat screen in the dome and its lamp, for dome flats.

    Served by the server-side ``flatscreen`` interface (ocabox-server ≥ 2.11, a ``flatscreen`` component with a
    ``driver``; which hardware switches the lamp is the server's concern). The lamp's vocabulary is ``'on'`` /
    ``'off'``, the values of the lamp axis of the optical graph.

    ``lamp`` is the reading. Where the hardware cannot read the lamp (on OCM: the lamp hangs on the ASA mount's fan
    output), the server answers it with 3002 and ``commanded`` is all there is: the last ``lampon`` / ``lampoff``
    the server sent, ``{'lamp': 'on' | 'off' | None, 'at': ISO UTC | None}`` (``None`` since the server started).
    A command is not a reading — the optics service, for one, does not take ``commanded`` as proof.
    """

    lamp = OcaBoxParam(default=None, doc="Flat screen lamp read from the device: 'on' / 'off'")
    commanded = OcaBoxParam(default=None, doc="Last lamp command the server sent: {lamp: 'on'|'off'|None, at}")

    async def aget_lamp(self, time_of_data_tolerance: float | None = None) -> str:
        logger.debug(f'Getting flat screen lamp from {self.tel_addr}')
        return await self.aget_value('lamp', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_lamp(self, callback: Optional[Callable] = None,
                              time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing flat screen lamp from {self.tel_addr}')
        return await self.subscribe('lamp', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_commanded(self, time_of_data_tolerance: float | None = None) -> Dict:
        logger.debug(f'Getting flat screen commanded lamp from {self.tel_addr}')
        return await self.aget_value('commanded', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_commanded(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing flat screen commanded lamp from {self.tel_addr}')
        return await self.subscribe('commanded', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_lampon(self) -> None:
        logger.info(f'{self.tel_addr}: flat screen lamp on')
        await self.aput_value('lampon')

    async def aput_lampoff(self) -> None:
        logger.info(f'{self.tel_addr}: flat screen lamp off')
        await self.aput_value('lampoff')
