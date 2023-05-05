from __future__ import annotations
import asyncio
import functools
import logging
import time as time_module

import param
from astropy.coordinates import EarthLocation, get_moon, get_sun, AltAz, SkyCoord
import astropy.units as u
from astropy.time import Time

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__.rsplit('.')[-1])

param.parameterized.async_executor = lambda f: asyncio.create_task(f())


class EphemerisData(param.Parameterized):
    latitude_deg = param.Number(default=0.0, doc="Latitude", constant=True)
    longitude_deg = param.Number(default=0.0, doc="Longitude", constant=True)
    height_m = param.Number(default=0.0, doc="Elevation over sea", constant=True)
    pressure_hPa = param.Number(default=0.0, doc="Pressure", constant=True)

    utc = param.Number(default=None, doc="UTC time timestamp")

    def __init__(self, **params):
        super().__init__(**params)
        self.task = None
        self.stop_running_event = asyncio.Event()
        self.obs_location = EarthLocation(lat=self.latitude_deg * u.deg,
                                          lon=self.longitude_deg * u.deg,
                                          height=self.height_m * u.m)

    def as_time_obj(self, time: float | Time | None = None) -> Time:
        if time is None:
            time = self.utc
        return self._as_time_obj(time)

    @staticmethod
    @functools.lru_cache()
    def _as_time_obj(time: float | Time) -> Time:
        if isinstance(time, Time):
            return time
        return Time.fromunix(time)

    def get_moon(self, time: float | Time | None =None) -> SkyCoord:
        t = self.as_time_obj(time)
        return self._get_moon(t)

    def get_sun(self, time: float | Time | None = None) -> SkyCoord:
        t = self.as_time_obj(time)
        return self._get_sun(t)

    @functools.lru_cache()
    def _get_moon(self, time: Time) -> SkyCoord:
        return get_moon(time)

    @functools.lru_cache()
    def _get_sun(self, time: Time) -> SkyCoord:
        return get_sun(time)

    def moon_altaz(self, time: float | Time | None = None)  -> AltAz:
        return self.get_moon(time).transform_to(self.get_obs_az_frame(time))

    def get_moon_phase(self, time: float | Time | None = None) -> float:
        m = self.get_moon(time)
        s = self.get_sun(time)
        elongation = m.separation(s)
        return self.get_moon(time).moon_phase

    def get_obs_az_frame(self, time: float | Time | None = None) -> AltAz:
        t = self.as_time_obj(time)
        return self._get_obs_az_frame(t)

    @functools.lru_cache()
    def _get_obs_az_frame(self, time: Time) -> AltAz:
        return AltAz(obstime=time,
                     location=self.obs_location,
                     pressure=self.pressure_hPa * u.hPa
                     )

    def run(self):
        self.stop_running_event = asyncio.Event()
        logger.info(f'Starting {self}')
        try:
            self.task = asyncio.create_task(self._run())
        except Exception as e:
            logger.error(f'Error starting {self}: {e}')
            raise

    async def _run(self):
        logger.info(f'Task starting {self}')
        while not self.stop_running_event.is_set():
            t = Time.now()
            self.utc = t.utc.unix

            await asyncio.wait([self.stop_running_event.wait(), asyncio.sleep(1)],
                               return_when=asyncio.FIRST_COMPLETED)
        logger.info(f'Task finished {self}')

    def stop(self):
        logger.info(f'Sync Stopping requested {self}')
        self._stop()

    async def astop(self):
        logger.info(f'Async Stopping requested {self}')
        self._stop()
        logger.info(f'Awaiting for task finish {self}')
        await self.task

    def _stop(self):
        self.stop_running_event.set()
        if self.task is not None:
            t = self.task
            self.task = None
            logger.info(f'Stopping {self}')
        else:
            logger.warning('Task EphemerisData is not running, so it can not be stopped')

    def __del__(self):
        logger.info(f'Stopping on destructor {self}')
        self._stop()
        if self.task is not None:
            logger.info(f'Canceling {self}')
            self.task.cancel()



class TreeEphemeris(TreeProvider):
    """
    This module provides current information about sky position of the celestial object and current time in  various timescales.
    address commands:
        - method1 - do stuff 1
        - method2 - do stuff 2
    """

    def __init__(self, component_name: str, source_name: str, **kwargs):
        self.data = EphemerisData()
        # self.data.run()
        self.data.param.watch(self.on_utc_changed, 'utc')
        super().__init__(component_name=component_name, source_name=source_name, subcontractor=None, **kwargs)
        logger.info(f'Created {self}')

    async def on_utc_changed(self, event: param.Event):
        logger.debug(f'UTC changed to {self.data.utc}')
        # TODO: send notification to subscribers, or update cache value?

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        user = request.user
        request_type = request.request_type
        try:
            command = request.address[request.index]
        except IndexError:
            raise AddressError(code=1001, message='The address does not contain a command.')

        if command == 'utc':
            # t = Time.now()
            # return Value(v=t.utc.unix, ts=time.time())
            return Value(v=self.data.utc, ts=time_module.time())

        if command == 'method2':
            timeout_control = "response string"
            return Value(v=timeout_control, ts=time_module.time())
        raise AddressError(code=1002, message=f'Unrecognised method for module {self.get_name()}')

    async def run(self):
        self.data.run()
        return await super().run()

    async def stop(self):
        await self.data.astop()
        return await super().stop()




