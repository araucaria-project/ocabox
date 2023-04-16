import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
import time

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ChangeFilter(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'change-filter', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.filterwheel = self.telescope.get_filterwheel('filterwheel')
        self.kwargs = kwargs
        self.id = id
        self.fil_wh_pos: int or None = None
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def _wait_to_move(self):
        while True:
            await asyncio.sleep(0.5)
            filter = self.proof_val(self.filterwheel.position)
            if isinstance(filter, int) and filter>-1:
                if filter-self.fil_wh_pos==0:
                    logger.debug(f'{self.id} {self.subcommand_name} is done')
                    self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                    self.info_callback['stream_5'](f'{self.id}')
                    break

    async def arun(self, step_id: str or None = None) -> int:
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        ZB08_FILT = {'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'B': 5, 'V': 6, 'Ic': 7}
        if isinstance(self.kwargs["filter"], int):
            self.fil_wh_pos = int(self.kwargs["filter"])
        elif isinstance(self.kwargs["filter"], str):
            if self.kwargs["filter"] in ZB08_FILT.keys():
                self.fil_wh_pos = ZB08_FILT[self.kwargs["filter"]]
            else:
                self.info_callback['stream_1'](
                    f'Filter index{self.kwargs["filter"]} is wrong, {self.parent.id} skipping')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                return 1
        else:
            self.info_callback['stream_1'](
                f'Filter index{self.kwargs["filter"]} is wrong, {self.parent.id} skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            return 1
        fit_pos = self.proof_val(self.filterwheel.position)
        if self.fil_wh_pos==fit_pos:
            self.info_callback['stream_1'](f'No need to change filter - skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            return 0
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} {self.kwargs["filter"]} started')
        await self.filterwheel.aput_position(int(self.fil_wh_pos))
        await self._wait_to_move()
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0