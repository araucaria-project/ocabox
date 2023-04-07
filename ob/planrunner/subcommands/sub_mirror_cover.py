import asyncio
import logging
from ob.planrunner.subcommand import SubCommand

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MirrorCover(SubCommand):


    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'mirror cover', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        super().__init__(id=self.id, parent=parent, subcommand_name=subcommand_name, **kwargs)

    async def _wait_for_move(self):
        await asyncio.sleep(15)
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        logger.debug(f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')

    async def arun(self, step_id: str or None = None) -> int:
        if 'open' in self.kwargs.keys():
            if self.kwargs['open']==True:
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} opening')
                logger.debug(f'{self.id} {self.subcommand_name} opening')
                if self.telescope.id == 'dev':
                    pass
                else:
                    await self.mount.aput_opencover()
                await self._wait_for_move()
            if self.kwargs['open']==False:
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} closing')
                logger.debug(f'{self.id} {self.subcommand_name} closing')
                if self.telescope.id == 'dev':
                    pass
                else:
                    await self.mount.aput_closecover()
                await self._wait_for_move()
        return 0