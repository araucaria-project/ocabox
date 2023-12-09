import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Focusing(BaseSubCommand):


    def __init__(self, id: str, parent: 'Command', name: str = 'focusing', **kwargs) -> None:
        self.kwargs = kwargs
        super().__init__(id=id, parent=parent, name=name, **kwargs)
        self.focuser = self.telescope.get_focuser()

    async def _wait_for_move(self, position) -> None:
        # TODO focuser_value get from config
        focuser_value = 5
        while True:
            await asyncio.sleep(0.5)
            foc_position = await self.value_proof_get(name='focus_pos',
                                                      awaitab=self.focuser.aget_position,
                                                      expect_type=int)
            if foc_position is not None:
                if (abs(int(foc_position) - int(position))) < focuser_value:
                    break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        logger.info(f'{self.id} started')
        self.info_callback['exec_json'](self.exec_json())
        if 'position' in self.kwargs.keys():
            position = self.kwargs['position']
            self.info_callback['stream_1'](f'{self.id} {self.name} moving to {position}')
            logger.debug(f'{self.id} {self.name} moving to {position}')
            await self.focuser.aput_move(int(position))
            await self._wait_for_move(position)
            logger.info(f'{self.id} done')
            self.info_callback['stream_1'](f'{self.id} {self.name} done')
            self.info_callback['stream_5'](f'{self.id}')
            self.done = True
            self.info_callback['exec_json'](self.exec_json())
            return 0
        else:
            self.info_callback['stream_1'](f'{self.id} {self.name} skipping - no position')
            logger.info(f'{self.id} skipping: no position set')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            return 0
