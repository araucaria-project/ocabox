import datetime
import time
from ob.planrunner.base_subcommand import BaseSubCommand
import logging
import asyncio
from typing import Callable, Dict, Any
import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, get_sun, get_body
from astropy.time import Time


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Wait(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 key: str, value: str, uobi: int,
                 name: str = 'wait', param: Dict[str, Any] or None = None) -> None:
        self.key = key
        self.value = value
        self.loc = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
        super().__init__(id=id, info_callback=info_callback,
                         telescope=telescope, name=name, uobi=uobi, param=param)
        self.info_dict = {'key': self.key, 'value': self.value}
        self.create_sub_command_string(**self.info_dict)

    async def _wait_exec(self, value: float) -> None:
        await asyncio.sleep(value)

    def _that_day_time(self, date: datetime, time_str: str) -> float:
        """
        Metgod gives time of time_str for day given by date_time_stamp (no matter what time in this date_time_stamp)
        :param date_time_stamp: day red from this timestamp
        :param time_str: time in str format
        :return: timestamp of date(date_time_stamp) and time(time_str)
        """
        d = date.strftime('%Y-%m-%d')
        myDate = f"{d} {time_str}"
        return time.mktime(datetime.datetime.strptime(myDate, "%Y-%m-%d %H:%M:%S").timetuple())

    async def _ut_exec(self, value: str) -> None:
        today = datetime.datetime.utcnow()
        target_t = self._that_day_time(date=today, time_str=value)
        now_t = time.mktime(datetime.datetime.utcnow().timetuple())
        if now_t >= target_t:
            tomorow = today + datetime.timedelta(days=1)
            target_t = self._that_day_time(date=tomorow, time_str=value)
        while True:
            now_t = time.mktime(datetime.datetime.utcnow().timetuple())
            if now_t >= target_t:
                break
            await asyncio.sleep(0)

    async def _wait_sun_exec(self, value: str, sun_rise: bool) -> bool:
        # TODO take loc from settings
        lo = EarthLocation(lat=self.loc['latitude'] * u.deg,
                           lon=self.loc['longitude'] * u.deg,
                           height=self.loc['elevation'] * u.m)
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
        await self.param['plan_status'].upd_status(id=self.id, field='started', value=True)
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
        await self.param['plan_status'].upd_status(id=self.id, field='done', value=True)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
