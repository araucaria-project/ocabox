from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Tertiary(TelescopeComponent):
    """Tertiary (M3) mirror.

    Read-back is served by the server-side tertiary device (ocabox-server
    ≥ 2.3.18, kind ``tertiaryOCA`` for ASA AutoSlew): ``nasmythport`` and the
    ``tertiarystatus`` dict plus its decomposed fields. Port numbers are the
    physical AutoSlew ports (jk15: 1=ADR6/beso, 2=ADR10/andor) — NOT 0-based;
    the observatory config maps them to instruments via ``tertiary_position``.
    """

    nasmythport = OcaBoxParam(default=0, doc="Current physical M3 nasmyth port")
    tertiarystatus = OcaBoxParam(default={}, doc="Full M3 status dict "
                                                 "(Moving, MotorOn, ErrorRaised, Angle, NasmythPort, PortName)")
    angle = OcaBoxParam(default=0.0, doc="M3 rotation angle [deg]")
    moving = OcaBoxParam(default=False, doc="True while M3 is rotating")
    motoron = OcaBoxParam(default=False, doc="True when M3 motor is powered")
    errorraised = OcaBoxParam(default=False, doc="True when M3 controller reports an error")
    portname = OcaBoxParam(default='', doc="Vendor name of the current port, e.g. 'ADR10'")

    async def aget_nasmythport(self) -> int:
        logger.debug(f'Getting tertiary nasmythport from {self.tel_addr}')
        return await self.aget_value('nasmythport')

    async def asubscribe_nasmythport(self, callback: Optional[Callable] = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary nasmythport from {self.tel_addr}')
        return await self.subscribe('nasmythport', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_tertiarystatus(self) -> Dict:
        logger.debug(f'Getting tertiarystatus from {self.tel_addr}')
        return await self.aget_value('tertiarystatus')

    async def asubscribe_tertiarystatus(self, callback: Optional[Callable] = None,
                                        time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiarystatus from {self.tel_addr}')
        return await self.subscribe('tertiarystatus', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_angle(self) -> float:
        logger.debug(f'Getting tertiary angle from {self.tel_addr}')
        return await self.aget_value('angle')

    async def asubscribe_angle(self, callback: Optional[Callable] = None,
                               time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary angle from {self.tel_addr}')
        return await self.subscribe('angle', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_moving(self) -> bool:
        logger.debug(f'Getting tertiary moving from {self.tel_addr}')
        return await self.aget_value('moving')

    async def asubscribe_moving(self, callback: Optional[Callable] = None,
                                time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary moving from {self.tel_addr}')
        return await self.subscribe('moving', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_motoron(self) -> bool:
        logger.debug(f'Getting tertiary motoron from {self.tel_addr}')
        return await self.aget_value('motoron')

    async def asubscribe_motoron(self, callback: Optional[Callable] = None,
                                 time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary motoron from {self.tel_addr}')
        return await self.subscribe('motoron', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_errorraised(self) -> bool:
        logger.debug(f'Getting tertiary errorraised from {self.tel_addr}')
        return await self.aget_value('errorraised')

    async def asubscribe_errorraised(self, callback: Optional[Callable] = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary errorraised from {self.tel_addr}')
        return await self.subscribe('errorraised', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_portname(self) -> str:
        logger.debug(f'Getting tertiary portname from {self.tel_addr}')
        return await self.aget_value('portname')

    async def asubscribe_portname(self, callback: Optional[Callable] = None,
                                  time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing tertiary portname from {self.tel_addr}')
        return await self.subscribe('portname', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aput_selectnasmythport(self, position: int) -> None:
        logger.debug(f'Putting tertiary selectnasmythport to position {position} in {self.tel_addr}')
        await self.aput_value('selectnasmythport', Position=position)
