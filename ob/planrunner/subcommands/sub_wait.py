import datetime
from ob.planrunner.base_subcommand import BaseSubCommand
import logging
import asyncio
from typing import Callable, Dict, Any
import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, get_sun
from astropy.time import Time
from ob.planrunner.coded_error import SequenceTreeError
from ob.planrunner.status import PlanStatusEnum


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Wait(BaseSubCommand):

    def __init__(
            self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
            key: str, value: str, uobi: int, name: str = 'wait', param: Dict[str, Any] or None = None) -> None:

        self.key = key
        self.value = value
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi, param=param)
        self.info_dict = {'key': self.key, 'value': self.value}
        self.create_sub_command_string(**self.info_dict)

    @staticmethod
    async def _wait_exec(value: float) -> None:
        await asyncio.sleep(value)

    @staticmethod
    async def _ut_exec(value: str) -> None:
        val = value.split(':')
        if len(val) == 2:
            h = int(val[0])
            m = int(val[1])
            s = 0
        elif len(val) == 3:
            h = int(val[0])
            m = int(val[1])
            s = int(val[2])
        else:
            raise SequenceTreeError
        while True:
            utc = datetime.datetime.utcnow()
            if utc.hour == h:
                if utc.minute >= m:
                    if utc.second >= s:
                        break
            await asyncio.sleep(0.1)

    async def _wait_sun_exec(self, value: str, sun_rise: bool) -> bool:
        loc = self.param['cfg_gen'].get_value(seq=['site', 'global', 'geo_location'], source='nats')
        lo = EarthLocation(lat=loc['lat'] * u.deg, lon=loc['lon'] * u.deg, height=loc['elev'] * u.m)
        try:
            val = float(value)
        except ValueError:
            inf = 'Wait sun alt value error, put float.'
            await self.journal.error(inf)
            logger.error(inf)
            return False
        w = 0
        while True:
            t = Time.now()
            sun = get_sun(t)
            sun_altaz = sun.transform_to(AltAz(location=lo))
            al = sun_altaz.alt.deg
            if w % 60 == 0:
                await self.journal.info(f'Wait sun pos.: {round(al, 2)} -> {val}')
            if sun_rise is True and val < al or sun_rise is False and val > al:
                break
            await asyncio.sleep(1)
            w += 1

    async def arun(self, step_id: str or None = None) -> int:
        inf = f'{self.id} {self.name} {self.key} {self.value} started.'
        await self.journal.info(inf)
        logger.info(inf)
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        self.info_callback['stream_1'](inf)
        if self.key == 'wait':
            await self._wait_exec(float(self.value))
        elif self.key == 'ut':
            await self._ut_exec(self.value)
        elif self.key == 'wait_sunrise':
            await self._wait_sun_exec(self.value, sun_rise=True)
        elif self.key == 'wait_sunset':
            await self._wait_sun_exec(self.value, sun_rise=False)
        else:
            pass
        inf = f'{self.id} {self.name} done.'
        self.info_callback['stream_1'](inf)
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(inf)
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
