from __future__ import annotations
import logging
from typing import Callable, Dict
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Guiding(TelescopeComponent):

    status = OcaBoxParam(default={}, doc="Guiding status")
    xxxx = OcaBoxParam(default=0.0, doc="xxxx")

    async def aget_status(self) -> Dict:
        logger.debug(f'Getting guiding status {self.tel_addr}')
        ret = await self.aget_value('status')
        return ret

    async def asubscribe_status(self, callback: Callable | None = None,
                                time_of_data_tolerance: float | None = None) -> None:
        logger.debug(f'Subscribing guiding status {self.tel_addr}')
        return await self.subscribe(param_name='status',
                                    callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_start_guiding(self) -> None:
        logger.debug(f'Putting start guiding to {self.tel_addr}')
        await self.aput_value('start_guiding')
