from __future__ import annotations
import logging
from typing import Callable, Dict, List
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam


logger = logging.getLogger(__name__.rsplit('.')[-1])


class GuidingController(TelescopeComponent):

    status = OcaBoxParam(default='', doc="Guiding status")
    exposure = OcaBoxParam(default=0.0, doc="Guiding exposure")
    period = OcaBoxParam(default=0.0, doc="Guiding period")
    calib_step = OcaBoxParam(default=0.0, doc="Guiding calibration step")
    calib_data = OcaBoxParam(default={}, doc="Guiding calibration data")

    #TODO get info about darks collection

    async def aget_status(self) -> str:
        logger.debug(f'Getting guiding status {self.tel_addr}')
        ret = await self.aget_value(param_name='status')
        return ret

    async def aget_exposure(self) -> float:
        logger.debug(f'Getting guiding exposure {self.tel_addr}')
        ret = await self.aget_value(param_name='exposure')
        return ret

    async def aget_period(self) -> float:
        logger.debug(f'Getting guiding exposure {self.tel_addr}')
        ret = await self.aget_value(param_name='period')
        return ret

    async def aget_calib_step(self) -> float:
        logger.debug(f'Getting guiding calibration step {self.tel_addr}')
        ret = await self.aget_value(param_name='calib_step')
        return ret

    async def aget_calib_data(self) -> Dict:
        logger.debug(f'Getting guiding calibration data {self.tel_addr}')
        ret = await self.aget_value(param_name='calib_data')
        return ret

    async def asubscribe_status(self, callback: Callable | None = None,
                                time_of_data_tolerance: float | None = None) -> None:
        logger.debug(f'Subscribing guiding status {self.tel_addr}')
        return await self.subscribe(param_name='status',
                                    callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_exposure(self, callback: Callable | None = None,
                                time_of_data_tolerance: float | None = None) -> None:
        logger.debug(f'Subscribing guiding status {self.tel_addr}')
        return await self.subscribe(param_name='exposure',
                                    callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_period(self, callback: Callable | None = None,
                                  time_of_data_tolerance: float | None = None) -> None:
        logger.debug(f'Subscribing guiding status {self.tel_addr}')
        return await self.subscribe(param_name='period',
                                    callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_calib_step(self, callback: Callable | None = None,
                                  time_of_data_tolerance: float | None = None) -> None:
        logger.debug(f'Subscribing guiding calibration step {self.tel_addr}')
        return await self.subscribe(param_name='calib_step',
                                    callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_calib_data(self, callback: Callable | None = None,
                                  time_of_data_tolerance: float | None = None) -> None:
        logger.debug(f'Subscribing guiding calibration data {self.tel_addr}')
        return await self.subscribe(param_name='calib_data',
                                    callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_start_guiding(self, star_select: List | None = None, mount_follow: bool = True) -> None:
        logger.debug(f'Putting start guiding to {self.tel_addr}')
        await self.aput_value(param_name='start_guiding', star_select=star_select, mount_follow=mount_follow)

    async def aput_start_calib(self) -> None:
        logger.debug(f'Putting start calibration to {self.tel_addr}')
        await self.aput_value(param_name='start_calib')

    async def aput_prep_master_dark(self, sub_no: int = 3) -> None:
        logger.debug(f'Putting prepare guiding master dark to {self.tel_addr}')
        await self.aput_value(param_name='prep_dark', sub_no=sub_no)

    async def aput_stop(self) -> None:
        logger.debug(f'Putting stop to {self.tel_addr}')
        await self.aput_value(param_name='stop')

    async def aput_preview(self) -> None:
        logger.debug(f'Putting guider preview to {self.tel_addr}')
        await self.aput_value(param_name='preview')

    async def aput_exposure(self, exp: float) -> None:
        logger.debug(f'Putting exposure time to {self.tel_addr}')
        await self.aput_value(param_name='exposure', exp=exp)

    async def aput_period(self, period: float) -> None:
        logger.debug(f'Putting guiding period to {self.tel_addr}')
        await self.aput_value(param_name='period', period=period)

    async def aput_calib_step(self, step: float) -> None:
        logger.debug(f'Putting guiding calibration step to {self.tel_addr}')
        await self.aput_value(param_name='calib_step', step=step)
