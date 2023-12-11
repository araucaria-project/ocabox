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
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(f'{self.id} started')
        if self.light == True:
            self.info_callback['stream_1'](f'{self.id} {self.name} turning on')
            logger.debug(f'{self.id} turning on')
            if self.telescope.id == 'dev':
                pass
            else:
                await self.mount.aput_domelamp_on()
        else:
            self.info_callback['stream_1'](f'{self.id} {self.name} turning off')
            logger.debug(f'{self.id} turning off')
            if self.telescope.id == 'dev':
                pass
            else:
                await self.mount.aput_domelamp_off()
            await self._wait_for_turn_on_off()
        self.info_callback['stream_5'](f'{self.id}')
        self.info_callback['stream_1'](f'{self.id} {self.name} done')
        logger.info(f'{self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
