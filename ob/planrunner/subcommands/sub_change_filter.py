import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
import time

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ChangeFilter(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'change-filter', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.filterwheel = self.telescope.get_filterwheel()
        self.kwargs = kwargs
        self.id = id
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def _wait_to_move(self, pos: int) -> None:
        while True:
            await asyncio.sleep(0.5)
            fit_pos = await self.get_value_position()
            if isinstance(fit_pos, int) and fit_pos>-1:
                if fit_pos==pos:
                    logger.debug(f'{self.id} {self.subcommand_name} is done')
                    self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                    self.info_callback['stream_5'](f'{self.id}')
                    break

    async def get_value_position(self):
        while True:
            val = self.filterwheel.position
            if isinstance(val, int):
                return val
            await asyncio.sleep(0.1)

    async def change_filter_pos_proof(self, pos: int) -> None or int:
        try:
            await self.filterwheel.aput_position(pos)
        except:
            try:
                await self.filterwheel.aput_position(pos)
            except:
                try:
                    await self.filterwheel.aput_position(pos)
                except:
                    logger.error(f'{self.id} {self.subcommand_name} filter aput_position error')
                    return 1

    async def arun(self, step_id: str or None = None) -> int:
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} {self.kwargs["filter"]} started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        ZB08_FILT = {'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'B': 5, 'V': 6, 'Ic': 7}
        if self.telescope.id=='dev':
            pos = int(self.kwargs["filter"])
        else:
            if self.kwargs["filter"] in ZB08_FILT.keys() and self.kwargs["filter"] is not None:
                pos = ZB08_FILT[self.kwargs["filter"]]
            else:
                self.info_callback['stream_1'](
                    f'Filter index{self.kwargs["filter"]} is wrong, {self.parent.id} skipping')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                return 1
        fit_pos = await self.get_value_position()
        if pos==fit_pos:
            self.info_callback['stream_1'](f'No need to change filter - skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            return 0

        # TODO this subcommand is freeze on aput_position -> change_filter_pos_proof
        res = await self.change_filter_pos_proof(pos)
        if res==1:
            self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} filter aput_position error, skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            return 1
        await self._wait_to_move(pos)
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0