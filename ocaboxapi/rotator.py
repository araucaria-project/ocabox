from __future__ import annotations
import logging
from typing import Callable

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Rotator(TelescopeComponent):

    ismoving = OcaBoxParam(default=0, doc="Rotator ismoving")
    mechanicalposition = OcaBoxParam(default=0, doc="Rotator mechanical position")
    position = OcaBoxParam(default=0, doc="Rotator position")
    reverse = OcaBoxParam(default=0, doc="Rotator reverse")
    stepsize = OcaBoxParam(default=0, doc="Rotator stepsize")
    targetposition = OcaBoxParam(default=0, doc="Rotator target position")

    async def aget_ismoving(self, time_of_data_tolerance: float | None = None) -> bool:
        logger.debug(f'Getting rotator is moving from {self.tel_addr}')
        ret = await self.aget_value('ismoving', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_ismoving(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing rotator is moving from {self.tel_addr}')
        return await self.subscribe('ismoving', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_mechanicalposition(self):
        logger.debug(f'Getting rotator mechanical position from {self.tel_addr}')
        ret = await self.aget_value('mechanicalposition', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_mechanicalposition(self,
                                            callback: Callable | None = None,
                                            time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing rotator mechanical position from {self.tel_addr}')
        return await self.subscribe('mechanicalposition',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_position(self, time_of_data_tolerance: float | None = None) -> float:
        logger.debug(f'Getting rotator position from {self.tel_addr}')
        ret = await self.aget_value('position', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_position(self,
                                            callback: Callable | None = None,
                                            time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing rotator position from {self.tel_addr}')
        return await self.subscribe('position',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_reverse(self, time_of_data_tolerance: float | None = None) -> bool:
        logger.debug(f'Getting rotator reverse state from {self.tel_addr}')
        ret = await self.aget_value('reverse', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_reverse(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing rotator reverse state from {self.tel_addr}')
        return await self.subscribe('reverse', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_stepsize(self, time_of_data_tolerance: float | None = None) -> float:
        logger.debug(f'Getting rotator stepsize from {self.tel_addr}')
        ret = await self.aget_value('stepsize', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_stepsize(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing rotator stepsize from {self.tel_addr}')
        return await self.subscribe('stepsize',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_targetposition(self, time_of_data_tolerance: float | None = None) -> float:
        logger.debug(f'Getting rotator target position from {self.tel_addr}')
        ret = await self.aget_value('targetposition', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_targetposition(self,
                                        callback: Callable | None = None,
                                        time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing rotator target position from {self.tel_addr}')
        return await self.subscribe('targetposition',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aput_reverse(self, reverse: bool) -> None:
        """
        True if the rotation and angular direction must be reversed to match the optical characteristcs
        """
        logger.debug(f'Putting rotator reverse to {self.tel_addr}')
        await self.aput_value('reverse', Reverse=reverse)

    async def aput_halt(self) -> None:
        logger.debug(f'Putting rotator halt to {self.tel_addr}')
        await self.aput_value('halt')

    async def aput_move(self, position: float) -> None:
        """
        Relative position to move in degrees from current Position.
        """
        logger.debug(f'Putting rotator move to {self.tel_addr}')
        await self.aput_value('move', Position=position)

    async def aput_moveabsolute(self, position: float) -> None:
        """
        Causes the rotator to move the absolute position of Position degrees.
        """
        logger.debug(f'Putting rotator move absolute to {self.tel_addr}')
        await self.aput_value('moveabsolute', Position=position)

    async def aput_movemechanical(self, position: float) -> None:
        """
        Causes the rotator to move the mechanical position of Position degrees.
        """
        logger.debug(f'Putting rotator move mechanical to {self.tel_addr}')
        await self.aput_value('movemechanical', Position=position)

    async def aput_sync(self, position: float) -> None:
        """
        Causes the rotator to sync to the position of Position degrees.
        """
        logger.debug(f'Putting rotator sync to {self.tel_addr}')
        await self.aput_value('sync', Position=position)