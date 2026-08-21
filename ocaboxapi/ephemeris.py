from __future__ import annotations
import logging
import time
from datetime import datetime
from typing import Callable, List
from ocaboxapi.telescopecomponent import Component, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Ephemeris(Component):

    utc = OcaBoxParam(default=None, doc="UTC time touple")

    async def aget_utc(self) -> float | None:
        """Retuens timestamp of utc time"""
        logger.debug(f'Getting utc from {self.my_address()}')
        ret = await self.aget_value('utc')
        return ret

    async def asubscribe_utc(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing utc from {self.my_address()}')
        return await self.subscribe('utc', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    @staticmethod
    def ts_to_datetime(timestamp: float|None) -> datetime|None:
        if timestamp is None:
            return None
        return datetime.fromtimestamp(timestamp)

