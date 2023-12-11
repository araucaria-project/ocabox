import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from typing import Callable, Dict


logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeScreenLight(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 light: bool, uobi: int, name: str = 'dome-screenlight') -> None:
        self.light = light
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi)
        self.mount = self.telescope.get_mount('mount')
        self.info_dict = {'light': self.light}
        self.create_sub_command_string(**self.info_dict)

    @staticmethod
    async def _wait_for_turn_on_off():
        await asyncio.sleep(15)

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        inf = f'{self.id} {self.name} started.'
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(inf)
        await self.journal.info(inf)

        if self.light is True:
            inf = f'{self.id} {self.name} turning on.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            if self.telescope.id == 'dev':
                pass
            else:
                await self.mount.aput_domelamp_on()
        else:
            inf = f'{self.id} {self.name} turning off.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            if self.telescope.id == 'dev':
                pass
            else:
                await self.mount.aput_domelamp_off()
            await self._wait_for_turn_on_off()

        inf = f'{self.id} {self.name} done.'
        self.info_callback['stream_5'](f'{self.id}')
        self.info_callback['stream_1'](inf)
        logger.info(inf)
        await self.journal.info(inf)
        self.done = True
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
