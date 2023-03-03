from __future__ import annotations
import logging
from typing import Callable, List
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class FilterWheel(TelescopeComponent):

    focusoffsets = OcaBoxParam(default=None, doc="Filter focus offsets")
    names = OcaBoxParam(default=None, doc="Filter names")
    position = OcaBoxParam(default=0, doc="Filterwheel position")

    async def aget_focusoffsets(self) -> List[int]:
        logger.debug(f'Getting focus offsets from {self.tel_addr}')
        ret = await self.aget_value('focusoffsets')
        return ret

    async def asubscribe_focusoffsets(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing focus offsets from {self.tel_addr}')
        return await self.subscribe('focusoffsets', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_names(self) -> List[str]:
        logger.debug(f'Getting filter names from {self.tel_addr}')
        ret = await self.aget_value('names')
        return ret

    async def asubscribe_names(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing focus offsets from {self.tel_addr}')
        return await self.subscribe('names', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_position(self) -> int:
        logger.debug(f'Getting filterwheel position from {self.tel_addr}')
        ret = await self.aget_value('position')
        return ret

    async def asubscribe_position(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing filterwheel position from {self.tel_addr}')
        return await self.subscribe('position', callback=callback, time_of_data_tolerance=time_of_data_tolerance)
