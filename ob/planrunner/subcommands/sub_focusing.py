import asyncio
import logging
from ob.planrunner.subcommand import SubCommand

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Focusing(SubCommand):


    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'focusing', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.id = id
        self.focuser = self.telescope.get_focuser()
        self.kwargs = kwargs
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def _wait_for_move(self, position) -> None:
        while True:
            foc_position = self.focuser.position
            await asyncio.sleep(0.5)
            if foc_position is not None:
                if (abs(int(foc_position) - int(position))) < 5:
                    logger.debug(f'{self.id} {self.subcommand_name} is done')
                    self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                    self.info_callback['stream_5'](f'{self.id}')
                    break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        if 'pos' in self.kwargs.keys():
            position = self.kwargs['pos']
            self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} moving to {position}')
            logger.debug(f'{self.id} {self.subcommand_name} moving to {position}')
            await self.focuser.aput_move(pos=position)
            await self._wait_for_move(position)
            self.done = True
            self.info_callback['exec_json'](self.exec_json())
            return 0
        else:
            self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} skipping - no position')
            logger.debug(f'{self.id} {self.subcommand_name} skipping - no position')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            return 0
