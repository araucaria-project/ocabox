from __future__ import annotations
import logging
from typing import Callable, Dict
import time
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class AccessGrantor(TelescopeComponent):
    current_user = OcaBoxParam(default=0.0, doc="User Controlling Telescope")
    timeout_current_control  = OcaBoxParam(default=0.0, doc="Timeout current telescope control")
    is_access = OcaBoxParam(default=0.0, doc="Is user still have telescope control")

    async def aget_current_user(self) -> Dict[str] | None:
        logger.debug(f'Getting telescope controlling user from {self.tel_addr}')
        ret = await self.aget_value('current_user')
        return ret

    async def asubscribe_current_user(self, callback: Callable | None = None,
                                      time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing telescope controlling user from {self.tel_addr}')
        return await self.subscribe('current_user', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_timeout_current_control(self) -> float | None:
        logger.debug(f'Getting telescope timeout current control from {self.tel_addr}')
        ret = await self.aget_value('timeout_current_control')
        return ret

    async def asubscribe_timeout_current_control(self, callback: Callable | None = None,
                                      time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing telescope timeout current control from {self.tel_addr}')
        return await self.subscribe('timeout_current_control',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_is_access(self) -> bool:
        logger.debug(f'Getting telescope is access from {self.tel_addr}')
        ret = await self.aget_value('is_access')
        return ret

    async def asubscribe_is_access(self, callback: Callable | None = None,
                                      time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing telescope is access from {self.tel_addr}')
        return await self.subscribe('is_access', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_take_control(self, for_how_long: float | None = None):
        logger.debug(f'Putting take_control to {self.tel_addr}')
        if for_how_long:
            timeout_reservation = time.time()+for_how_long
        else:
            timeout_reservation = None
        return await self.aput_value('take_control', timeout_reservation=timeout_reservation)

    async def aput_break_control(self):
        logger.debug(f'Putting break_control to {self.tel_addr}')
        return await self.aput_value('break_control')

    async def aput_return_control(self):
        logger.debug(f'Putting return_control to {self.tel_addr}')
        return await self.aput_value('return_control')
