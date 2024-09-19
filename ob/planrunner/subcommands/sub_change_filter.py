import datetime
from typing import Callable, Dict, Any
import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from ob.planrunner.status import PlanStatusEnum

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ChangeFilter(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 filter: str, uobi: int,  name: str = 'change-filter', param: Dict[str, Any] or None = None) -> None:
        self.filter = filter
        super().__init__(id=id, info_callback=info_callback, telescope=telescope,
                         name=name, uobi=uobi, param=param)
        self.filterwheel = self.telescope.get_filterwheel()
        self.info_dict = {'filter': self.filter}
        self.create_sub_command_string(**self.info_dict)

    async def _wait_to_move(self, pos: int) -> None:
        logger.info('Wait to move...')
        while True:
            await asyncio.sleep(0.2)
            fit_pos = await self.value_proof_get(name='fw_pos',
                                                 awaitab=self.filterwheel.aget_position,
                                                 expect_type=int)
            if isinstance(fit_pos, int) and fit_pos > -1:
                if fit_pos==pos:
                    logger.info('Wait to move done')
                    break

    async def arun(self, step_id: str or None = None) -> int:
        inf = f'{self.id} {self.name} {self.filter} started'
        logger.info(inf)
        self.info_callback['stream_1'](inf)
        await self.journal.info(inf)
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        # filter_dict = await self.filterwheel.aget_names()
        filter_dict = await self.get_filters_dict()
        try:
            pos = filter_dict[self.filter]
        except (LookupError, TypeError):
            inf = f'{self.id} {self.name} filter index {self.filter} is wrong, error.'
            self.info_callback['stream_1'](
                f'Filter index{self.filter} is wrong, {self.id} error')
            await self.journal.error(inf)
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 2

        fit_pos = await self.value_proof_get(name='fw_pos',
                                             awaitab=self.filterwheel.aget_position,
                                             expect_type=int)
        if pos == fit_pos:
            inf = f'{self.id} {self.name} no need to change filter, skipping.'
            self.info_callback['stream_1'](inf)
            self.info_callback['stream_5'](f'{self.id}')
            await self.journal.info(inf)
            logger.info(inf)
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0
        fp = await self.proof_put(awaitab=self.filterwheel.aput_position, pos=pos)
        if not fp:
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            inf = f'Can not execute change filter, program stopping'
            logger.error(inf)
            await self.journal.error(inf)
            return 2
        await self._wait_to_move(pos)
        inf = f'{self.id} {self.name} done.'
        await self.journal.info(inf)
        logger.info(inf)
        self.info_callback['stream_1'](inf)
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
