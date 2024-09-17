import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from typing import Callable, Dict, Any
from pyaraucaria.focus import Focus

from ob.planrunner.status import PlanStatusEnum

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Focusing(BaseSubCommand):


    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 uobi: int, position: float = None, auto: bool = False, name: str = 'focusing',
                 param: Dict[str, Any] or None = None) -> None:
        self.position = position
        super().__init__(id=id, info_callback=info_callback, telescope=telescope,
                         name=name, uobi=uobi, param=param)
        self.focuser = self.telescope.get_focuser()
        self.auto = auto
        self.info_dict = {'position': self.position, 'auto_focus': self.auto}
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
                    await asyncio.sleep(1)
                    break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        inf = f'{self.id} {self.name} started.'
        logger.info(inf)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        await self.journal.info(inf)

        if self.position is not None and self.auto is False:
            inf = f'{self.id} {self.name} moving to {self.position}.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            # await self.focuser.aput_move(int(self.position))
            fm = await self.proof_put(awaitab=self.focuser.aput_move, pos=int(self.position))
            if not fm:
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                inf = f'Can not move focuser, program stopping'
                logger.error(inf)
                await self.journal.error(inf)
                return 2
            await self._wait_for_move(self.position)
        elif self.position is None and self.auto is True:
            rang = self.gen_conf.get_value([self.telescope.id, 'focuser', 'focusing_range'])
            #rang = [14000, 17000]
            inf = f'{self.id} {self.name} calculate focus position from {self.fits_focus_folder_actual}.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            try:
                sharp, calc_metadata = Focus.calculate(fits_path=self.fits_focus_folder_actual, range=rang)
            except TypeError:
                inf = f'{self.id} {self.name} wrong focus calculation.'
                self.info_callback['stream_1'](inf)
                await self.journal.warning(inf)
                logger.warning(inf)
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                self.info_callback['exec_json'](self.exec_json())
                return 2
            if rang[1] > sharp > rang[0]:
                inf = f'{self.id} {self.name} calculated focus position {round(sharp)}.'
                self.info_callback['stream_1'](inf)
                await self.journal.info(inf)
                logger.info(inf)
                # await self.focuser.aput_move(round(sharp))
                fm = await self.proof_put(awaitab=self.focuser.aput_move, pos=round(sharp))
                if not fm:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not move focuser, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    return 2
                await self._wait_for_move(sharp)
            else:
                inf = f'{self.id} {self.name} wrong focus calculation: {sharp}.'
                self.info_callback['stream_1'](inf)
                await self.journal.warning(inf)
                logger.warning(inf)
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                self.info_callback['exec_json'](self.exec_json())
                return 2
        else:
            inf = f'{self.id} {self.name} wrong input.'
            self.info_callback['stream_1'](inf)
            await self.journal.warning(inf)
            logger.warning(inf)
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
            self.info_callback['exec_json'](self.exec_json())
            return 0

        inf = f'{self.id} {self.name} done.'
        logger.info(inf)
        self.info_callback['stream_1'](inf)
        await self.journal.info(inf)
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json())
        return 0
