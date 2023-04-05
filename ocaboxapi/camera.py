from __future__ import annotations
import logging
import time
from typing import Callable, List
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Camera(TelescopeComponent):

    name = OcaBoxParam(default='', doc="Camera name")
    sensorname = OcaBoxParam(default='', doc="Camera sensor name")
    ccdtemperature = OcaBoxParam(default=0.0, doc="Camera ccd temperature")
    setccdtemperature = OcaBoxParam(default=0.0, doc="Camera set ccd temperature")
    binx = OcaBoxParam(default=0, doc="Camera binx")
    biny = OcaBoxParam(default=0, doc="Camera biny")
    camerastate = OcaBoxParam(default=0, doc="Camera state")
    gain = OcaBoxParam(default=0, doc="Camera gain")
    offset = OcaBoxParam(default=0, doc="Camera offset")
    offsets = OcaBoxParam(default=0, doc="Avaliable Camera offsets")
    offsetmax = OcaBoxParam(default=0, doc="Maximum offset value of that this camera supports")
    offsetmin = OcaBoxParam(default=0, doc="Minimum offset value of that this camera supports")
    subexposureduration = OcaBoxParam(default=0.0, doc="Camera subexposure duration")
    percentcompleted = OcaBoxParam(default=0.0, doc="Camera exposure percent competed")
    coolerpower = OcaBoxParam(default=0.0, doc="Camera cooler power level")
    cooleron = OcaBoxParam(default=False, doc="Camera is cooler on")
    imageready = OcaBoxParam(default=False, doc="Camera is image ready")
    imagearray = OcaBoxParam(default=[0], doc="Camera image array")
    readoutmode = OcaBoxParam(default=0, doc="Camera readoutmode")
    readoutmodes = OcaBoxParam(default=[0], doc="Camera readoutmodes")
    fastreadout = OcaBoxParam(default=False, doc="Camera fast readout")
    numx = OcaBoxParam(default=0, doc="Camera numx")
    numy = OcaBoxParam(default=0, doc="Camera numy")
    startx = OcaBoxParam(default=0, doc="Camera startx")
    starty = OcaBoxParam(default=0, doc="Camera starty")


    camerastate_to_code = {
        'cameraidle': 0,
        'camerawaiting': 1,
        'cameraexposing': 2,
        'camerareading': 3,
        'cameradownload': 4,
        'cameraerror': 5,
    }

    camerastate_code_to_status = {v: k for k, v in camerastate_to_code.items()}

    # TODO: MMirrkk: Why override `aget_name` and `asubscribe_name`?
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

    async def asubscribe_sensorname(self, callback: Callable | None = None,
                                    time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing camera sensor name from {self.tel_addr}')
        return await self.subscribe('sensorname', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_ccdtemperature(self) -> float:
        logger.debug(f'Getting ccd temperature from {self.tel_addr}')
        ret = await self.aget_value('ccdtemperature')
        return ret

    async def asubscribe_ccdtemperature(self, callback: Callable | None = None,
                                        time_of_data_tolerance: float | None = None):
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

    async def asubscribe_camerastate(self, callback: Callable | None = None,
                                     time_of_data_tolerance: float | None = None):
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

    async def asubscribe_coolerpower(self, callback: Callable | None = None,
                                     time_of_data_tolerance: float | None = None):
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

    async def aget_offsets(self) -> []:
        logger.debug(f'Getting camera offsets from {self.tel_addr}')
        ret = await self.aget_value('offsets')
        return ret

    async def aget_offsetmin(self) -> int:
        logger.debug(f'Getting camera offsetmin from {self.tel_addr}')
        ret = await self.aget_value('offsetmin')
        return ret

    async def aget_offsetmax(self) -> int:
        logger.debug(f'Getting camera offsetmax from {self.tel_addr}')
        ret = await self.aget_value('offsetmax')
        return ret

    async def aget_subexposureduration(self) -> float:
        logger.debug(f'Getting subexposure duration from {self.tel_addr}')
        ret = await self.aget_value('subexposureduration')
        return ret

    async def asubscribe_subexposureduration(self, callback: Callable | None = None,
                                             time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing subexposure duration from {self.tel_addr}')
        return await self.subscribe('subexposureduration',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_percentcompleted(self) -> int:
        logger.debug(f'Getting exposure percent competed from {self.tel_addr}')
        ret = await self.aget_value('percentcompleted')
        return ret

    async def asubscribe_percentcompleted(self, callback: Callable | None = None,
                                          time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing exposure percent competed from {self.tel_addr}')
        return await self.subscribe('percentcompleted',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_imagearray(self) -> List[int]:
        logger.debug(f'Getting imagearray from {self.tel_addr}')
        ret = await self.aget_value('imagearray', request_timeout=time.time() + 600)
        return ret

    async def aget_imageready(self) -> bool:
        logger.debug(f'Getting imageready from {self.tel_addr}')
        ret = await self.aget_value('imageready')
        return ret

    async def asubscribe_imageready(self, callback: Callable | None = None,
                                    time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing image ready from {self.tel_addr}')
        return await self.subscribe('imageready', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_readoutmode(self) -> int:
        logger.debug(f'Getting readoutmode from {self.tel_addr}')
        ret = await self.aget_value('readoutmode')
        return ret

    async def asubscribe_readoutmode(self, callback: Callable | None = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing readoutmode from {self.tel_addr}')
        return await self.subscribe('readoutmode', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_readoutmodes(self) -> List[str]:
        logger.debug(f'Getting readoutmodes from {self.tel_addr}')
        ret = await self.aget_value('readoutmodes')
        return ret

    async def asubscribe_readoutmodes(self, callback: Callable | None = None,
                                      time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing readoutmodes from {self.tel_addr}')
        return await self.subscribe('readoutmodes', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_fastreadout(self) -> bool:
        logger.debug(f'Getting fastreadout from {self.tel_addr}')
        ret = await self.aget_value('fastreadout')
        return ret

    async def asubscribe_fastreadout(self, callback: Callable | None = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing fastreadout from {self.tel_addr}')
        return await self.subscribe('fastreadout', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_numx(self) -> int:
        logger.debug(f'Getting numx from {self.tel_addr}')
        ret = await self.aget_value('numx')
        return ret

    async def asubscribe_numx(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing numx from {self.tel_addr}')
        return await self.subscribe('numx', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_numy(self) -> int:
        logger.debug(f'Getting numy from {self.tel_addr}')
        ret = await self.aget_value('numy')
        return ret

    async def asubscribe_numy(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing numy from {self.tel_addr}')
        return await self.subscribe('numy', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_startx(self) -> int:
        logger.debug(f'Getting startx from {self.tel_addr}')
        ret = await self.aget_value('startx')
        return ret

    async def asubscribe_startx(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing startx from {self.tel_addr}')
        return await self.subscribe('startx', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_starty(self) -> int:
        logger.debug(f'Getting starty from {self.tel_addr}')
        ret = await self.aget_value('starty')
        return ret

    async def asubscribe_starty(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing starty from {self.tel_addr}')
        return await self.subscribe('starty', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_setccdtemperature(self) -> float:
        logger.debug(f'Getting set ccd temperature from {self.tel_addr}')
        ret = await self.aget_value('setccdtemperature')
        return ret

    async def asubscribe_setccdtemperature(self, callback: Callable | None = None,
                                           time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing set ccd temperature from {self.tel_addr}')
        return await self.subscribe('setccdtemperature',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

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

    async def aput_readoutmode(self, romode: int) -> None:
        logger.debug(f'Putting readoutmode to {self.tel_addr}')
        await self.aput_value('readoutmode', ReadoutMode=romode)

    async def aput_fastreadout(self, fastreadout: bool) -> None:
        logger.debug(f'Putting fastreadout to {self.tel_addr}')
        await self.aput_value('fastreadout', FastReadout=fastreadout)

    async def aput_numx(self, numx: int) -> None:
        logger.debug(f'Putting numx to {self.tel_addr}')
        await self.aput_value('numx', NumX=numx)

    async def aput_numy(self, numy: int) -> None:
        logger.debug(f'Putting numy to {self.tel_addr}')
        await self.aput_value('numy', NumY=numy)

    async def aput_startx(self, startx: int) -> None:
        logger.debug(f'Putting startx to {self.tel_addr}')
        await self.aput_value('startx', StartX=startx)

    async def aput_starty(self, starty: int) -> None:
        logger.debug(f'Putting starty to {self.tel_addr}')
        await self.aput_value('starty', StartY=starty)
