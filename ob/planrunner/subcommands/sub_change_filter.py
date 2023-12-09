import datetime

import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand


logger = logging.getLogger(__name__.rsplit('.')[-1])


class ChangeFilter(BaseSubCommand):

    def __init__(self, id: str, parent: 'Command', filter: str, uobi: int,  name: str = 'change-filter') -> None:
        self.filter = filter
        super().__init__(id=id, parent=parent, name=name, uobi=uobi)
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
        logger.info(f'{self.id} started')
        self.info_callback['stream_1'](f'{self.id} {self.name} {self.filter} started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        filter_dict = await self.filterwheel.aget_names()
        try:
            pos = filter_dict[self.filter]
        except KeyError:
            self.info_callback['stream_1'](
                f'Filter index{self.filter} is wrong, {self.id} skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 1

        fit_pos = await self.value_proof_get(name='fw_pos',
                                             awaitab=self.filterwheel.aget_position,
                                             expect_type=int)
        if pos == fit_pos:
            self.info_callback['stream_1'](f'No need to change filter, skipping')
            self.info_callback['stream_5'](f'{self.id}')
            logger.info(f'{self.id} no need to change filter, skipping')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0

        # TODO this subcommand is freeze on aput_position -> change_filter_pos_proof
        res = await self.change_filter_pos_proof(pos)
        if res==1:
            self.info_callback['stream_1'](f'{self.id} {self.name} filter aput_position error, skipping')
            self.info_callback['stream_5'](f'{self.id}')
            logger.info(f'{self.id} filter aput_position error, skipping')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 1
        await self._wait_to_move(pos)
        logger.info(f'{self.id} done')
        self.info_callback['stream_1'](f'{self.id} {self.name} done')
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
