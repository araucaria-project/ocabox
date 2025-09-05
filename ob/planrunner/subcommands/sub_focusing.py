import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from typing import Callable, Dict, Any, Optional
from pyaraucaria.focus import Focus

from ob.planrunner.iter_async import AsyncListIter
from ob.planrunner.status import PlanStatusEnum
from ob.planrunner.utils import run_in_thread_executor, run_in_process_executor

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Focusing(BaseSubCommand):


    def __init__(
            self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
            uobi: int, position: float = None, auto: bool = False, name: str = 'focusing',
            param: Optional[Dict[str, Any]] = None, filter_offset: bool = False,
            seq_data: Optional['Seq']= None) -> None:

        self.position = position
        self.filter_offset = filter_offset
        self.seq_data = seq_data
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi, param=param)
        self.focuser = self.telescope.get_focuser()
        self.auto = auto
        self.info_dict = {'position': self.position, 'auto_focus': self.auto}
        self.create_sub_command_string(**self.info_dict)

    async def _wait_for_move(self, position) -> None:
        # TODO focuser_value get from config
        focuser_value = 5
        while True:
            await asyncio.sleep(0.5)
            foc_position = await self.value_proof_get(
                name='focus_pos', awaitab=self.focuser.aget_position, expect_type=int
            )
            if foc_position is not None:
                if (abs(int(foc_position) - int(position))) < focuser_value:
                    await asyncio.sleep(1)
                    break

    async def calculate_filter_offset(self) -> Optional[int]:
        filter_dict = await self.get_filters_dict()
        try:
            ordered_filter_slot = filter_dict[self.seq_data.filter_]
        except (LookupError, TypeError, ValueError):
            return None
        filers_config = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'filterwheel', 'filters'
        ], source='nats')
        if self.seq_data.filer_slot_before_change == ordered_filter_slot:
            logger.info(f'No filter change so no focus offset change.')
            return 0
        old_focus_position = None
        new_focus_position = None
        async for _filter_dat in AsyncListIter(filers_config):
            if _filter_dat['position'] == self.seq_data.filer_slot_before_change:
                old_focus_position = _filter_dat['focus_offset']
            elif _filter_dat['position'] == ordered_filter_slot:
                new_focus_position = _filter_dat['focus_offset']
        if old_focus_position is not None and new_focus_position is not None:
            new_position = new_focus_position - old_focus_position
            logger.info(
                f'Offset focus from filter slot {self.seq_data.filer_slot_before_change}'
                f' -> {ordered_filter_slot} is {new_position}.'
            )
        else:
            new_position = None
        return new_position

    async def arun(self, step_id: Optional[str] = None) -> int:
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        inf = f'{self.id} {self.name} started.'
        logger.info(inf)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        await self.journal.info(inf)

        # Simple focus change
        if self.position is not None and self.auto is False and self.filter_offset is False:
            inf = f'{self.id} {self.name} moving to {self.position}.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            fm = await self.proof_put(awaitab=self.focuser.aput_move, pos=int(self.position))
            if not fm:
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                inf = f'Can not move focuser, program stopping'
                logger.error(inf)
                await self.journal.error(inf)
                await self.status_error_publish(
                    level='critical',
                    description=inf,
                    plan_runner_quits=True
                )
                return 2
            await self._wait_for_move(self.position)

        # Filter focus offset
        elif self.position is None and self.auto is False and self.filter_offset is True:
            inf = f'{self.id} {self.name} filter focus offset starting.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            focus_offset = await self.calculate_filter_offset()
            if focus_offset is None:
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                inf = f'Can not calculate filter focus offset (check config), program stopping.'
                logger.error(inf)
                await self.journal.error(inf)
                await self.status_error_publish(
                    level='critical',
                    description=inf,
                    plan_runner_quits=True
                )
                return 2
            if focus_offset != 0:
                current_position = await self.value_proof_get(
                    name='focus_pos', awaitab=self.focuser.aget_position, expect_type=int
                )
                if current_position is None:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not get current focus position, program stopping.'
                    logger.error(inf)
                    await self.journal.error(inf)
                    await self.status_error_publish(
                        level='critical',
                        description=inf,
                        plan_runner_quits=True
                    )
                    return 2
                new_position = focus_offset + current_position
                inf = f'Filter focus offset is {focus_offset}, focus changing to {new_position}.'
                logger.info(inf)
                await self.journal.info(inf)
                fm = await self.proof_put(awaitab=self.focuser.aput_move, pos=int(new_position))
                if not fm:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not move focuser (filter offset), program stopping.'
                    logger.error(inf)
                    await self.journal.error(inf)
                    await self.status_error_publish(
                        level='critical',
                        description=inf,
                        plan_runner_quits=True
                    )
                    return 2
                await self._wait_for_move(new_position)
            else:
                inf = f'Filter focus offset is 0, no focus change.'
                logger.info(inf)
                await self.journal.info(inf)

        # Final autofocus change
        elif self.position is None and self.auto is True and self.filter_offset is False:
            rang_dict = self.param['cfg_gen'].get_value(seq=[
                'telescopes', self.telescope.id, 'observatory', 'components', 'focuser', 'focusing_range'
            ], source='nats')
            try:
                rang = [rang_dict['min'], rang_dict['max']]
            except (LookupError, TypeError):
                logger.error(f'No focusing range in focuser in general config')
                rang = [0, 50000]
            inf = f'{self.id} {self.name} calculate focus position from {self.fits_focus_folder_actual}.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            if self.seq_data.focus_method is not None:
                focus_method = self.seq_data.focus_method
            else:
                focus_method = 'rms_quad'
            logger.info(f'Focusing method: {focus_method}')
            try:
                sharp, calc_metadata = await run_in_thread_executor(
                    self.fits_focus_folder_actual, "FOCUS", None, 10, focus_method, rang,
                    func=Focus.calculate
                )
            except TypeError:
                inf = f'{self.id} {self.name} wrong focus calculation.'
                self.info_callback['stream_1'](inf)
                await self.journal.warning(inf)
                logger.warning(inf)
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                self.info_callback['exec_json'](self.exec_json())
                await self.status_error_publish(
                    level='critical',
                    description=inf,
                    plan_runner_quits=True
                )
                return 2
            if calc_metadata['status'] == 'ok' and rang[1] > sharp > rang[0]:
                inf = f'{self.id} {self.name} calculated focus position {round(sharp)}.'
                self.info_callback['stream_1'](inf)
                await self.journal.info(inf)
                logger.info(inf)
                fm = await self.proof_put(awaitab=self.focuser.aput_move, pos=round(sharp))
                if not fm:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not move focuser, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    await self.status_error_publish(
                        level='critical',
                        description=inf,
                        plan_runner_quits=True
                    )
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
                await self.status_error_publish(
                    level='critical',
                    description=inf,
                    plan_runner_quits=True
                )
                return 2
        # Mode is not recognized
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
