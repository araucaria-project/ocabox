import datetime
import time
from ob.planrunner.subcommand import SubCommand
import logging
import asyncio


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Wait(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'wait', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.kwargs = kwargs
        self.id = id
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def _wait_exec(self, value: float) -> None:
        await asyncio.sleep(value)

    async def _ut_exec(self, value: str) -> None:
        while True:
            myDate = f"{datetime.datetime.today().strftime('%Y-%m-%d')} {value}"
            target_t = time.mktime(datetime.datetime.strptime(myDate, "%Y-%m-%d %H:%M:%S").timetuple())
            now_t = time.mktime(datetime.datetime.utcnow().timetuple())
            if now_t >= target_t:
                break
            await asyncio.sleep(0)

    async def _wait_sunrise_exec(self, value: float) -> None:
        pass

    async def _wait_sunset_exec(self, value: float) -> None:
        pass

    async def arun(self, step_id: str or None = None) -> int:
        logger.info(f'{self.id} started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        self.info_callback['stream_1'](f"{self.id} {self.subcommand_name} {self.kwargs['key']} started")
        logger.info(f'{self.id} started')
        if self.kwargs['key'] == 'wait':
            await self._wait_exec(float(self.kwargs['value']))
        elif self.kwargs['key'] == 'ut':
            await self._ut_exec(self.kwargs['value'])
        elif self.kwargs['key'] == 'wait_sunrise':
            await self._wait_sunrise_exec(self.kwargs['value'])
        elif self.kwargs['key'] == 'wait_sunset':
            await self._wait_sunset_exec(self.kwargs['value'])
        else:
            pass
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0