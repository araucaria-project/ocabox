import asyncio
import logging
from obs_pln_parser.subcommand import SubCommand


log = logging.getLogger(__name__.rsplit('.')[-1])


class ChangeFilter(SubCommand):

    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.subcommand_name = 'ChangeFilter'
        self.telescope = parent.telescope
        self.filterwheel = self.telescope.get_filterwheel('filterwheel')
        self.kwargs = kwargs
        self.id = id
        super().__init__(id=id, parent=parent, subcommand_name=self.subcommand_name, **kwargs)

    async def _wait_to_move(self):
        while True:
            filter = self.filterwheel.position
            await asyncio.sleep(1)
            if int(filter) - int(self.kwargs['filter']) == 0:
                log.debug(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None):
        log.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} FILTER:{self.kwargs["filter"]} started')
        await self.filterwheel.aput_position(self.kwargs['filter'])
        await self._wait_to_move()
        await asyncio.sleep(5)