from __future__ import annotations

from typing import Callable

import logging
from ocaboxapi.component import OcaBoxParam
from ocaboxapi.telescopecomponent import TelescopeComponent

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CCTV(TelescopeComponent):

    cam_name = OcaBoxParam(default=None, doc="Camera name")
    # didn't find a way to get this from API
    ir = OcaBoxParam(default=None, doc="is IR on")
    snapshot = OcaBoxParam(default=None, doc="CCTV camera snapshot")

    async def aput_ir(self, on: bool) -> None:
        logger.debug(f'Putting cctv ir to {on}')
        await self.aput_value('ir', state=on)

    async def aget_ir(self) -> bool | None:
        logger.debug(f'Getting cctv ir status')
        ret =  await self.aget_value('ir')
        return ret

    async def asubscribe_ir(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing cctv ir status {self.tel_addr}')
        return await self.subscribe('ir', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_snapshot(self):
        logger.debug(f'Getting snapshot from {self.tel_addr}')
        ret = await self.aget_value('snapshot')
        return ret

    async def asubscribe_snapshot(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing snapshot from {self.tel_addr}')
        return await self.subscribe('snapshot', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

