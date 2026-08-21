from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Tertiary(TelescopeComponent):
    """Tertiary (M3) mirror.

    Read-back is served by the server-side ``tertiary`` interface
    (ocabox-server ≥ 2.3.18; which hardware implementation serves it is the
    server's concern): ``nasmythport`` and the ``tertiarystatus`` dict plus
    its decomposed fields. Port numbers are the physical mount ports — NOT
    0-based; the observatory config maps them to instruments via
    ``tertiary_position``.

    A controller fault surfaces through the standard error model: every
    decomposed read raises ``OcaboxDeviceError`` (server code 4009) while the
    controller reports an error — there is no device-specific error flag to
    poll. ``tertiarystatus`` stays readable as the raw diagnostic view.
    """

    nasmythport = OcaBoxParam(default=0, doc="Current physical M3 nasmyth port")
    tertiarystatus = OcaBoxParam(default={}, doc="Full M3 status dict "
                                                 "(Moving, MotorOn, ErrorRaised, Angle, NasmythPort, PortName)")
    angle = OcaBoxParam(default=0.0, doc="M3 rotation angle [deg]")
    moving = OcaBoxParam(default=False, doc="True while M3 is rotating")
    motoron = OcaBoxParam(default=False, doc="True when M3 motor is powered")
    portname = OcaBoxParam(default='', doc="Device name of the current port")

    async def aget_nasmythport(self, time_of_data_tolerance: float | None = None) -> int | None:
        logger.debug(f'Getting tertiary nasmythport from {self.tel_addr}')
        return await self.aget_value('nasmythport', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_nasmythport(self, callback: Optional[Callable] = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary nasmythport from {self.tel_addr}')
        return await self.subscribe('nasmythport', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_tertiarystatus(self, time_of_data_tolerance: float | None = None) -> Dict | None:
        logger.debug(f'Getting tertiarystatus from {self.tel_addr}')
        return await self.aget_value('tertiarystatus', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_tertiarystatus(self, callback: Optional[Callable] = None,
                                        time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiarystatus from {self.tel_addr}')
        return await self.subscribe('tertiarystatus', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_angle(self, time_of_data_tolerance: float | None = None) -> float | None:
        logger.debug(f'Getting tertiary angle from {self.tel_addr}')
        return await self.aget_value('angle', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_angle(self, callback: Optional[Callable] = None,
                               time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary angle from {self.tel_addr}')
        return await self.subscribe('angle', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_moving(self, time_of_data_tolerance: float | None = None) -> bool | None:
        logger.debug(f'Getting tertiary moving from {self.tel_addr}')
        return await self.aget_value('moving', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_moving(self, callback: Optional[Callable] = None,
                                time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary moving from {self.tel_addr}')
        return await self.subscribe('moving', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_motoron(self, time_of_data_tolerance: float | None = None) -> bool | None:
        logger.debug(f'Getting tertiary motoron from {self.tel_addr}')
        return await self.aget_value('motoron', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_motoron(self, callback: Optional[Callable] = None,
                                 time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary motoron from {self.tel_addr}')
        return await self.subscribe('motoron', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_portname(self, time_of_data_tolerance: float | None = None) -> str | None:
        logger.debug(f'Getting tertiary portname from {self.tel_addr}')
        return await self.aget_value('portname', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_portname(self, callback: Optional[Callable] = None,
                                  time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary portname from {self.tel_addr}')
        return await self.subscribe('portname', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aput_selectnasmythport(self, position: int) -> None:
        logger.debug(f'Putting tertiary selectnasmythport to position {position} in {self.tel_addr}')
        await self.aput_value('selectnasmythport', Position=position)
