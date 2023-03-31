import asyncio
import logging
from ob.planrunner.subcommand import SubCommand


logger = logging.getLogger(__name__.rsplit('.')[-1])


class ChangeFilter(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'change filter', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.filterwheel = self.telescope.get_filterwheel('filterwheel')
        self.kwargs = kwargs
        self.id = id
        self.fil_wh_pos: int = 0
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name, **kwargs)

    async def _wait_to_move(self):
        while True:
            filter = self.filterwheel.position
            await asyncio.sleep(1)
            if int(filter) - self.fil_wh_pos == 0:
                logger.debug(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> int:
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        ZB08_FILT = {'u': 11, 'g': 12, 'r': 13, 'i': 14, 'z': 15, 'B': 16, 'V': 17, 'Ic': 18}
        try:
            self.fil_wh_pos = int(self.kwargs["filter"])
        except ValueError:
            if self.kwargs["filter"] in ZB08_FILT.keys():
                self.fil_wh_pos = ZB08_FILT[self.kwargs["filter"]]
            else:
                self.info_callback['stream_1'](
                    f'Filter index{self.kwargs["filter"]} is wrong, {self.parent.id} skipping')
                return 1
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} {self.kwargs["filter"]} started')
        await self.filterwheel.aput_position(self.fil_wh_pos)
        await self._wait_to_move()
        await asyncio.sleep(5)
        return 0