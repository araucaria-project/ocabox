import datetime
import time
from ob.planrunner.base_subcommand import BaseSubCommand
import logging
import asyncio


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Wait(BaseSubCommand):

    def __init__(self, id: str, parent: 'Command', key: str, value: str, uobi: int, name: str = 'wait') -> None:
        self.key = key
        self.value = value
        super().__init__(id=id, parent=parent, name=name, uobi=uobi)
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

    async def _wait_sunrise_exec(self, value: str) -> None:
        pass

    async def _wait_sunset_exec(self, value: str) -> None:
        pass

    async def arun(self, step_id: str or None = None) -> int:
        logger.info(f'{self.id} started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        self.info_callback['stream_1'](f"{self.id} {self.name} {self.key} started")
        logger.info(f'{self.id} started')
        if self.key == 'wait':
            await self._wait_exec(float(self.value))
        elif self.key == 'ut':
            await self._ut_exec(self.value)
        elif self.key == 'wait_sunrise':
            await self._wait_sunrise_exec(self.value)
        elif self.key == 'wait_sunset':
            await self._wait_sunset_exec(self.value)
        else:
            pass
        self.info_callback['stream_1'](f'{self.id} {self.name} done')
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
