import datetime
from typing import Callable, Dict, Any
import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand


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

    async def change_filter_pos_proof(self, pos: int) -> None or int:
        t = datetime.datetime.now()
        try:
            await self.filterwheel.aput_position(pos)
            logger.info(f'{self.id} {self.name} filter position done in {datetime.datetime.now()-t}')
        except Exception as e:
            logger.error(f'{self.id} {self.name} filter position error after {datetime.datetime.now()-t}: {e}')
            try:
                logger.warning(f'{self.id} filter change 2-nd try')
                await self.filterwheel.aput_position(pos)
            except:
                try:
                    logger.warning(f'{self.id} filter change 3-rd try')
                    await self.filterwheel.aput_position(pos)
                except:
                    logger.error(f'{self.id} filter aput_position error')
                    return 1

    async def arun(self, step_id: str or None = None) -> int:
        inf = f'{self.id} {self.name} {self.filter} started'
        logger.info(inf)
        self.info_callback['stream_1'](inf)
        await self.journal.info(inf)
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, field='started', value=True)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        filter_dict = await self.filterwheel.aget_names()
        try:
            pos = filter_dict[self.filter]
        except KeyError:
            inf = f'{self.id} {self.name} filter index {self.filter} is wrong, skipping.'
            self.info_callback['stream_1'](
                f'Filter index{self.filter} is wrong, {self.id} skipping')
            await self.journal.warning(inf)
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, field='skipped', value=True)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 1

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
            await self.param['plan_status'].upd_status(id=self.id, field='skipped', value=True)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0

        # TODO this subcommand is freeze on aput_position -> change_filter_pos_proof
        res = await self.change_filter_pos_proof(pos)
        if res == 1:
            inf = f'{self.id} {self.name} filter aput position error, skipping.'
            self.info_callback['stream_1'](inf)
            self.info_callback['stream_5'](f'{self.id}')
            logger.info(inf)
            await self.journal.error(inf)
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, field='skipped', value=True)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 1
        await self._wait_to_move(pos)
        inf = f'{self.id} {self.name} done.'
        await self.journal.info(inf)
        logger.info(inf)
        self.info_callback['stream_1'](inf)
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, field='done', value=True)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
