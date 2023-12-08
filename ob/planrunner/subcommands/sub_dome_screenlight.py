import asyncio
import logging
from ob.planrunner.subcommand import SubCommand

logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeScreenLight(SubCommand):


    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'dome-screenlight', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name, **kwargs)

    async def _wait_for_turn_on_off(self):
        await asyncio.sleep(15)

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        logger.info(f'{self.id} started')
        if 'light' in self.kwargs.keys():
            if self.kwargs['light']==True:
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} turning on')
                logger.debug(f'{self.id} turning on')
                if self.telescope.id == 'dev':
                    pass
                else:
                    await self.mount.aput_domelamp_on()
            if self.kwargs['light']==False:
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} turning off')
                logger.debug(f'{self.id} turning off')
                if self.telescope.id == 'dev':
                    pass
                else:
                    await self.mount.aput_domelamp_off()
                await self._wait_for_turn_on_off()
        self.info_callback['stream_5'](f'{self.id}')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        logger.info(f'{self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0