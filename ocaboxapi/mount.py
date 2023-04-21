from __future__ import annotations
import logging
from typing import Callable
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Mount(TelescopeComponent):

    rightascension = OcaBoxParam(default=0.0, doc="Mount rightascension")
    declination = OcaBoxParam(default=0.0, doc="Mount declination")
    azimuth = OcaBoxParam(default=0.0, doc="Mount azimuth")
    altitude = OcaBoxParam(default=0.0, doc="Mount altitude")
    athome = OcaBoxParam(default=False, doc="Mount is athome")
    atpark = OcaBoxParam(default=False, doc="Mount is atpark")
    slewing = OcaBoxParam(default=False, doc="Mount is slewing")
    tracking = OcaBoxParam(default=False, doc="Mount is tracking")
    ispulseguiding = OcaBoxParam(default=False, doc="Mount is pulseguiding")
    motorstatus = OcaBoxParam(default='', doc="Mount motorstatus")
    commandstring = OcaBoxParam(default='', doc="Mount motorstatus")

    async def aget_ra(self) -> float:
        logger.debug(f'Getting mount RA from {self.tel_addr}')
        ret = await self.aget_value('rightascension')
        return ret

    async def asubscribe_ra(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount RA from {self.tel_addr}')
        return await self.subscribe('rightascension', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_dec(self) -> float:
        logger.debug(f'Getting mount DEC from {self.tel_addr}')
        ret = await self.aget_value('declination')
        return ret

    async def asubscribe_dec(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount DEC from {self.tel_addr}')
        return await self.subscribe('declination', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_az(self) -> float:
        logger.debug(f'Getting mount AZ from {self.tel_addr}')
        ret = await self.aget_value('azimuth')
        return ret

    async def asubscribe_az(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount AZ from {self.tel_addr}')
        return await self.subscribe('azimuth', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_alt(self) -> float:
        logger.debug(f'Getting mount ALT from {self.tel_addr}')
        ret = await self.aget_value('altitude')
        return ret

    async def asubscribe_alt(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount ALT from {self.tel_addr}')
        return await self.subscribe('altitude', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_athome(self) -> bool:
        logger.debug(f'Getting mount athome from {self.tel_addr}')
        ret = await self.aget_value('athome')
        return ret

    async def asubscribe_athome(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount athome from {self.tel_addr}')
        return await self.subscribe('athome', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_atpark(self) -> bool:
        logger.debug(f'Getting mount atpark from {self.tel_addr}')
        ret = await self.aget_value('atpark')
        return ret

    async def asubscribe_atpark(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount atpark from {self.tel_addr}')
        return await self.subscribe('atpark', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_slewing(self) -> bool:
        logger.debug(f'Getting mount slewing from {self.tel_addr}')
        ret = await self.aget_value('slewing')
        return ret

    async def asubscribe_slewing(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount slewing from {self.tel_addr}')
        return await self.subscribe('slewing', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_tracking(self) -> bool:
        logger.debug(f'Getting mount tracking from {self.tel_addr}')
        ret = await self.aget_value('tracking')
        return ret

    async def asubscribe_tracking(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount tracking from {self.tel_addr}')
        return await self.subscribe('tracking', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_ispulseguiding(self) -> bool:
        logger.debug(f'Getting mount ispulseguiding from {self.tel_addr}')
        ret = await self.aget_value('ispulseguiding')
        return ret

    async def asubscribe_ispulseguiding(self, callback: Callable | None = None,
                                        time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount ispulseguiding from {self.tel_addr}')
        return await self.subscribe('ispulseguiding',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_motorstatus(self) -> str:
        logger.debug(f'Getting mount motorstatus from {self.tel_addr}')
        ret = await self.aget_value('motorstatus')
        return ret

    async def asubscribe_motorstatus(self, callback: Callable | None = None,
                                        time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount motorstatus from {self.tel_addr}')
        return await self.subscribe('motorstatus',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aput_slewtocoo(self, ra: float, dec: float) -> None:
        logger.debug(f'Putting slew coo to {self.tel_addr}')
        await self.aput_value('slewtocoordinates', RightAscension=ra, Declination=dec)

    async def aput_slewtocoo_async(self, ra: float, dec: float) -> None:
        logger.debug(f'Putting slew coo async to {self.tel_addr}')
        await self.aput_value('slewtocoordinatesasync', RightAscension=ra, Declination=dec)

    async def aput_slewtoaltaz(self, az: float, alt: float) -> None:
        logger.debug(f'Putting slew altaz to {self.tel_addr}')
        await self.aput_value('slewtoaltaz', Azimuth=az, Altitude=alt)

    async def aput_slewtoaltaz_async(self, az: float, alt: float) -> None:
        logger.debug(f'Putting slew altaz async to {self.tel_addr}')
        await self.aput_value('slewtoaltazasync', Azimuth=az, Altitude=alt)

    async def aput_tracking(self, track: bool) -> None:
        logger.debug(f'Putting tracking to {self.tel_addr}')
        await self.aput_value('tracking', Tracking=track)

    async def aput_abortslew(self) -> None:
        logger.debug(f'Putting abortslew to {self.tel_addr}')
        await self.aput_value('abortslew')

    async def aput_park(self) -> None:
        logger.debug(f'Putting park to {self.tel_addr}')
        await self.aput_value('park')

    async def aput_unpark(self) -> None:
        logger.debug(f'Putting unpark to {self.tel_addr}')
        await self.aput_value('unpark')

    async def aput_findhome(self) -> None:
        logger.debug(f'Putting findhome to {self.tel_addr}')
        await self.aput_value('findhome')

    async def aput_action(self, action: str, param: str | None = None) -> None:
        logger.debug(f'Putting action to {self.tel_addr}')
        await self.aput_value('action', Action=action, Parameters=param)

    async def aput_opencover(self) -> None:
        logger.debug(f'Putting telescope opencover to {self.tel_addr}')
        await self.aput_value('action', Action='telescope:opencover', Parameters='')

    async def aput_closecover(self) -> None:
        logger.debug(f'Putting telescope closecover to {self.tel_addr}')
        await self.aput_value('action', Action='telescope:closecover', Parameters='')

    async def aput_motoron(self) -> None:
        logger.debug(f'Putting telescope motoron to {self.tel_addr}')
        await self.aput_value('motoron')

    async def aput_motoroff(self) -> None:
        logger.debug(f'Putting telescope motoroff to {self.tel_addr}')
        await self.aput_value('motoroff')

    async def aput_domelamp_on(self) -> None:
        logger.debug(f'Putting dome lamp on to {self.tel_addr}')
        await self.aput_value('domeflatlampon')

    async def aput_domelamp_off(self) -> None:
        logger.debug(f'Putting dome lamp off to {self.tel_addr}')
        await self.aput_value('domeflatlampoff')
