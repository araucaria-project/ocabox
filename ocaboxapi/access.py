from __future__ import annotations
import logging
from typing import Callable

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class AccessGrantor(TelescopeComponent):
    current_user = OcaBoxParam(default=0.0, doc="User Controlling Telescope")

    async def aget_current_user(self) -> int:
        logger.debug(f'Getting telescope controlling user from {self.tel_addr}')
        ret = await self.aget_value('current_user')
        return ret

    async def asubscribe_current_user(self, callback: Callable | None = None,
                                      time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing telescope controlling user from {self.tel_addr}')
        return await self.subscribe('current_user', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_take_control(self, time: float):
        logger.debug(f'Putting take_control to {self.tel_addr}')
        return await self.aput_value('take_control', timeout_reservation=time)

    async def aput_break_control(self):
        logger.debug(f'Putting break_control to {self.tel_addr}')
        return await self.aput_value('break_control')

    async def aput_return_control(self):
        logger.debug(f'Putting return_control to {self.tel_addr}')
        return await self.aput_value('return_control')

