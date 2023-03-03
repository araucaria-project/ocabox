from __future__ import annotations
import logging
from typing import Callable
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Camera(TelescopeComponent):

    name = OcaBoxParam(default='', doc="Camera name")
    sensorname = OcaBoxParam(default='', doc="Camera sensor name")
    ccdtemperature = OcaBoxParam(default=0.0, doc="Camera ccd temperature")
    binx = OcaBoxParam(default=0, doc="Camera binx")
    biny = OcaBoxParam(default=0, doc="Camera biny")
    camerastate = OcaBoxParam(default=0, doc="Camera state")
    gain = OcaBoxParam(default=0, doc="Camera gain")
    offset = OcaBoxParam(default=0, doc="Camera offset")
    subexposureduration = OcaBoxParam(default=0.0, doc="Camera subexposure duration")
    percentcompleted = OcaBoxParam(default=0.0, doc="Camera exposure percent competed")
    coolerpower = OcaBoxParam(default=0.0, doc="Camera cooler power level")
    cooleron = OcaBoxParam(default=False, doc="Camera is cooler on")


    camerastate_to_code = {
        'cameraidle': 0,
        'camerawaiting': 1,
        'cameraexposing': 2,
        'camerareading': 3,
        'cameradownload': 4,
        'cameraerror': 5,
    }

    camerastate_code_to_status = {v: k for k, v in camerastate_to_code.items()}

    async def aget_name(self) -> str:
        logger.debug(f'Getting camera name from {self.tel_addr}')
        ret = await self.aget_value('name')
        return ret

    async def asubscribe_name(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera name from {self.tel_addr}')
        return await self.subscribe('name', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_sensorname(self) -> str:
        logger.debug(f'Getting camera sensor name from {self.tel_addr}')
        ret = await self.aget_value('sensorname')
        return ret

    async def asubscribe_sensorname(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera sensor name from {self.tel_addr}')
        return await self.subscribe('sensorname', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_ccdtemperature(self) -> float:
        logger.debug(f'Getting ccd temperature from {self.tel_addr}')
        ret = await self.aget_value('ccdtemperature')
        return ret

    async def asubscribe_ccdtemperature(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing ccd temperature from {self.tel_addr}')
        return await self.subscribe('ccdtemperature', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_binx(self) -> int:
        logger.debug(f'Getting camera binx from {self.tel_addr}')
        ret = await self.aget_value('binx')
        return ret

    async def asubscribe_binx(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera binx from {self.tel_addr}')
        return await self.subscribe('binx', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_biny(self) -> int:
        logger.debug(f'Getting camera biny from {self.tel_addr}')
        ret = await self.aget_value('biny')
        return ret

    async def asubscribe_biny(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera biny from {self.tel_addr}')
        return await self.subscribe('biny', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_camerastate(self) -> int:
        logger.debug(f'Getting camerastate from {self.tel_addr}')
        ret = await self.aget_value('camerastate')
        return ret

    async def asubscribe_camerastate(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camerastate from {self.tel_addr}')
        return await self.subscribe('camerastate', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_cooleron(self) -> bool:
        logger.debug(f'Getting camera cooleron from {self.tel_addr}')
        ret = await self.aget_value('cooleron')
        return ret

    async def asubscribe_cooleron(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera cooleron from {self.tel_addr}')
        return await self.subscribe('cooleron', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_coolerpower(self) -> float:
        logger.debug(f'Getting camera cooler power from {self.tel_addr}')
        ret = await self.aget_value('coolerpower')
        return ret

    async def asubscribe_coolerpower(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera cooler power from {self.tel_addr}')
        return await self.subscribe('coolerpower', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_gain(self) -> int:
        logger.debug(f'Getting camera gain from {self.tel_addr}')
        ret = await self.aget_value('gain')
        return ret

    async def asubscribe_gain(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera gain from {self.tel_addr}')
        return await self.subscribe('gain', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_offset(self) -> int:
        logger.debug(f'Getting camera offset from {self.tel_addr}')
        ret = await self.aget_value('offset')
        return ret

    async def asubscribe_offset(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera offset from {self.tel_addr}')
        return await self.subscribe('offset', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_subexposureduration(self) -> float:
        logger.debug(f'Getting subexposure duration from {self.tel_addr}')
        ret = await self.aget_value('subexposureduration')
        return ret

    async def asubscribe_subexposureduration(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing subexposure duration from {self.tel_addr}')
        return await self.subscribe('subexposureduration', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_percentcompleted(self) -> int:
        logger.debug(f'Getting exposure percent competed from {self.tel_addr}')
        ret = await self.aget_value('percentcompleted')
        return ret

    async def asubscribe_percentcompleted(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing exposure percent competed from {self.tel_addr}')
        return await self.subscribe('percentcompleted', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_binx(self, binx: int) -> None:
        logger.debug(f'Putting binx to {self.tel_addr}')
        await self.aput_value('binx', BinX=binx)

    async def aput_biny(self, biny: int) -> None:
        logger.debug(f'Putting binx to {self.tel_addr}')
        await self.aput_value('biny', BinY=biny)

    async def aput_cooleron(self, cooleron: bool) -> None:
        logger.debug(f'Putting cooler on to {self.tel_addr}')
        await self.aput_value('cooleron', CoolerOn=cooleron)

    async def aput_gain(self, gain: int) -> None:
        logger.debug(f'Putting gain to {self.tel_addr}')
        await self.aput_value('gain', Gain=gain)

    async def aput_offset(self, offset: int) -> None:
        logger.debug(f'Putting offset to {self.tel_addr}')
        await self.aput_value('offset', Offset=offset)

    async def aput_setccdtemperature(self, temp: float) -> None:
        logger.debug(f'Putting set ccd temperature to {self.tel_addr}')
        await self.aput_value('setccdtemperature', SetCCDTemperature=temp)

    async def aput_subexposureduration(self, duration: float) -> None:
        logger.debug(f'Putting subexposure duration to {self.tel_addr}')
        await self.aput_value('subexposureduration', SubExposureDuration=duration)

    async def aput_startexposure(self, duration: float, light: bool) -> None:
        logger.debug(f'Putting start exposure to {self.tel_addr}')
        await self.aput_value('startexposure', Duration=duration, Light=light)

    async def aput_stopexposure(self) -> None:
        logger.debug(f'Putting stop exposure to {self.tel_addr}')
        await self.aput_value('stopexposure')

    async def aput_abortexposure(self) -> None:
        logger.debug(f'Putting abort exposure to {self.tel_addr}')
        await self.aput_value('abortexposure')
