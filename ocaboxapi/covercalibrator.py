from __future__ import annotations
import logging
from typing import Callable, List
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CoverCalibrator(TelescopeComponent):

    coverstate = OcaBoxParam(default=0, doc="Telescope cover state")

    cover_status_to_code = {
        'closed': 1,
        'moving': 2,
        'open': 3,
    }
    cover_code_to_status = {v: k for k, v in cover_status_to_code.items()}


    async def aget_coverstate(self) -> int:
        logger.debug(f'Getting cover state from {self.tel_addr}')
        ret = await self.aget_value('coverstate')
        return ret

    async def asubscribe_coverstate(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing cover state from {self.tel_addr}')
        return await self.subscribe('coverstate', callback=callback, time_of_data_tolerance=time_of_data_tolerance)