from __future__ import annotations
import logging
from typing import Callable, List
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CoverCalibrator(TelescopeComponent):

    coverstate = OcaBoxParam(default=0, doc="Telescope cover state")
    calibratorstate = OcaBoxParam(default=0, doc="Calibrator state")
    brightness = OcaBoxParam(default=0, doc="Calibrator brightness")

    cover_status_to_code = {
        'closed': 1,
        'moving': 2,
        'open': 3,
    }
    cover_code_to_status = {v: k for k, v in cover_status_to_code.items()}

    async def aget_coverstate(self, time_of_data_tolerance: float | None = None) -> int:
        logger.debug(f'Getting cover state from {self.tel_addr}')
        ret = await self.aget_value('coverstate', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_coverstate(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing cover state from {self.tel_addr}')
        return await self.subscribe('coverstate', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_calibratorstate(self, time_of_data_tolerance: float | None = None) -> int:
        logger.debug(f'Getting calibrator state from {self.tel_addr}')
        ret = await self.aget_value('calibratorstate', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_calibratorstate(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing calibrator state from {self.tel_addr}')
        return await self.subscribe('calibratorstate', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_brightness(self, time_of_data_tolerance: float | None = None) -> int:
        logger.debug(f'Getting calibrator brightness from {self.tel_addr}')
        ret = await self.aget_value('brightness', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_brightness(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing calibrator brightness from {self.tel_addr}')
        return await self.subscribe('brightness', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_calibratoroff(self) -> None:
        logger.debug(f'Putting calibrator off to {self.tel_addr}')
        await self.aput_value('calibratoroff')

    async def aput_calibratoron(self, brightness: int) -> None:
        logger.debug(f'Putting calibrator on to {self.tel_addr}')
        await self.aput_value('calibratoron', Brightness=brightness)

    async def aput_closecover_dev(self) -> None:
        """
        Note: this method works only for dev telescope
        """
        logger.debug(f'Putting closecover on to {self.tel_addr}')
        await self.aput_value('closecover')

    async def aput_opencover_dev(self) -> None:
        """
        Note: this method works only for dev telescope
        """
        logger.debug(f'Putting opencover on to {self.tel_addr}')
        await self.aput_value('opencover')

    async def aput_closecover(self) -> None:
        """
        Note: this method works only for dev telescope
        """
        logger.debug(f'Putting closecover on to {self.tel_addr}')
        await self.aput_value('closecover')

    async def aput_opencover(self) -> None:
        """
        Note: this method works only for dev telescope
        """
        logger.debug(f'Putting opencover on to {self.tel_addr}')
        await self.aput_value('opencover')
