from __future__ import annotations
import logging
from typing import Callable
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Focuser(TelescopeComponent):

    position = OcaBoxParam(default=0, doc="Focuser position")
    tempcomp = OcaBoxParam(default=False, doc="Focuser temperature compensation")
    ismoving = OcaBoxParam(default=False, doc="Focuser is moving")
    fansstatus = OcaBoxParam(default=0, doc="Mirror fans status")

    async def aget_position(self) -> int:
        logger.debug(f'Getting focuser position from {self.tel_addr}')
        ret = await self.aget_value('position')
        return ret

    async def asubscribe_position(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing focuser position from {self.tel_addr}')
        return await self.subscribe('position', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_tempcomp(self) -> bool:
        logger.debug(f'Getting temp. compensation from {self.tel_addr}')
        ret = await self.aget_value('tempcomp')
        return ret

    async def asubscribe_tempcomp(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing temp. compensation from {self.tel_addr}')
        return await self.subscribe('tempcomp', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_fansstatus(self):
        logger.debug(f'Getting dome fans status from {self.tel_addr}')
        ret = await self.aget_value('fansstatus')
        return ret

    async def asubscribe_fansstatus(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing dome fans status from {self.tel_addr}')
        return await self.subscribe('fansstatus',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_ismoving(self) -> bool:
        logger.debug(f'Getting focuser is moving from {self.tel_addr}')
        ret = await self.aget_value('ismoving')
        return ret

    async def asubscribe_ismoving(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing focuser is moving from {self.tel_addr}')
        return await self.subscribe('ismoving', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_move(self, pos: int) -> None:
        logger.debug(f'Putting focuser move to {self.tel_addr}')
        await self.aput_value('move', Position=pos)

    async def aput_halt(self) -> None:
        logger.debug(f'Putting focuser halt to {self.tel_addr}')
        await self.aput_value('halt')

    async def aput_tempcomp(self, tempcomp: bool) -> None:
        logger.debug(f'Putting temp. compensation to {self.tel_addr}')
        await self.aput_value('tempcomp', TempComp=tempcomp)

    async def aput_fansturnon(self) -> None:
        logger.debug(f'Putting dome fans turn on {self.tel_addr}')
        await self.aput_value('fansturnon')

    async def aput_fansturnoff(self) -> None:
        logger.debug(f'Putting dome fans turn off to {self.tel_addr}')
        await self.aput_value('fansturnoff')
