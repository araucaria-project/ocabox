import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Focusing(BaseSubCommand):


    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 position: float, uobi: int, name: str = 'focusing', param: Dict[str, Any] or None = None) -> None:
        self.position = position
        super().__init__(id=id, info_callback=info_callback, telescope=telescope,
                         name=name, uobi=uobi, param=param)
        self.focuser = self.telescope.get_focuser()
        self.info_dict = {'position': self.position}
        self.create_sub_command_string(**self.info_dict)

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
        await self.param['plan_status'].upd_status(id=self.id, field='started', value=True)
        inf = f'{self.id} {self.name} started.'
        logger.info(inf)
        await self.journal.info(inf)

        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        inf = f'{self.id} {self.name} moving to {self.position}.'
        self.info_callback['stream_1'](inf)
        await self.journal.debug(inf)
        logger.debug(inf)
        await self.focuser.aput_move(int(self.position))
        await self._wait_for_move(self.position)
        inf = f'{self.id} {self.name} done.'
        logger.info(inf)
        self.info_callback['stream_1'](inf)
        await self.journal.info(inf)
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, field='done', value=True)
        self.info_callback['exec_json'](self.exec_json())
        return 0
