import asyncio
import logging
import os
import pwd
import time
from typing import Callable, Dict, Any, Optional

from ob.planrunner.base_subcommand import BaseSubCommand
from ob.planrunner.status import PlanStatusEnum


logger = logging.getLogger(__name__.rsplit('.')[-1])


class RotatorMove(BaseSubCommand):

    POSITION_TYPES = ["absolute", "mechanical"]

    def __init__(
            self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
            position: Optional[float], position_type: str, uobi: int, name: str = 'rotator',
            param: Optional[Dict[str, Any]] = None) -> None:

        self.position = position
        self.position_type = position_type
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi, param=param)
        self.rotator = self.telescope.get_rotator()
        self.info_dict = {"position": position, "position_type": position_type}
        self.slew_timeout: float = 180.0
        self.slew_tolerance: float = 0.15
        self.mount_type: Optional[str] = None
        self.create_sub_command_string(**self.info_dict)

    def _on_position(self, current_position: float, target_position: float) -> bool:
        if (abs(target_position - current_position)) < self.slew_tolerance \
                or (abs(target_position - current_position)) > 360.0 - self.slew_tolerance:
            return True
        else:
            return False

    async def _get_current_position(self) -> Optional[float]:
        if self.position_type == 'absolute':
            current_pos = await self.value_proof_get(
                name='rotator_abs_pos', awaitab=self.rotator.aget_position, expect_type=float, log=True
            )
        elif self.position_type == 'mechanical':
            current_pos = await self.value_proof_get(
                name='rotator_mech_pos', awaitab=self.rotator.aget_mechanicalposition, expect_type=float, log=True
            )

        else:
            logger.warning(f"No position type, selecting absolute")
            current_pos = await self.value_proof_get(
                name='rotator_abs_pos', awaitab=self.rotator.aget_position, expect_type=float, log=True
            )
        return current_pos

    async def _move(self, position: float) -> bool:
        if self.position_type == 'absolute':
            return await self.proof_put(
                awaitab=self.rotator.aput_moveabsolute, position=position
            )
        elif self.position_type == 'mechanical':
            return await self.proof_put(
                awaitab=self.rotator.aput_movemechanical, position=position
            )

        else:
            logger.warning(f"No position type, selecting absolute")
            return await self.proof_put(
                awaitab=self.rotator.aput_moveabsolute, position=position
            )

    async def _wait_to_move(self, position: float) -> bool:
        logger.info(f'Starting rotator wait to move: {position}')
        slew_start_time = time.time()
        while True:
            await asyncio.sleep(0.5)
            current_pos = await self._get_current_position()

            if current_pos is not None: # and current_if_slewing is False:
                if self._on_position(current_position=current_pos, target_position=position):
                    inf = f'Rotator {self.position_type} position on place, set: {position} current: {current_pos}'
                    await asyncio.sleep(2) # Give time to settle
                    logger.info(inf)
                    await self.journal.debug(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
                    return True
            if time.time() > slew_start_time + self.slew_timeout:
                inf = f'Rotator {self.position_type} move get timeout {self.slew_timeout}s.'
                logger.error(inf)
                await self.journal.debug(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
                return False

    async def get_from_config_general(self) -> None:
        self.mount_type = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'mount', 'type'
        ], source='nats')
        # _slew_timeout = self.param['cfg_gen'].get_value(seq=[
        #     'telescopes', self.telescope.id, 'observatory', 'components', 'rotator', 'move_timeout'
        # ], source='nats')
        # if _slew_timeout is not None:
        #     self.slew_timeout = _slew_timeout
        # _slew_tolerance = self.param['cfg_gen'].get_value(seq=[
        #     'telescopes', self.telescope.id, 'observatory', 'components', 'rotator', 'move_tolerance'
        # ], source='nats')
        # if _slew_tolerance is not None:
        #     self.slew_tolerance = _slew_tolerance

    async def arun(self, step_id: Optional[str] = None) -> int:
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        inf = f'{self.id} {self.name} started.'
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(inf)
        await self.journal.info(inf)

        await self.get_from_config_general()

        if self.mount_type == "eq":
            inf = f"{self.id} {self.name} no rotator for eq mount, rotator move skipping"
            self.info_callback['stream_1'](inf)
            self.info_callback['stream_5'](f'{self.id}')
            logger.info(inf)
            await self.journal.info(inf)
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0

        if self.position is None or 0 > self.position or self.position >= 360:
            inf = f'{self.id} {self.name} wrong rotator position {self.position} (must be 0-360), quiting.'
            self.info_callback['stream_1'](inf)
            self.info_callback['stream_5'](f'{self.id}')
            logger.error(inf)
            await self.journal.error(inf)
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            await self.status_error_publish(level='critical', description=inf, plan_runner_quits=True)
            return 2

        current_pos = await self._get_current_position()
        if current_pos is None:
            inf = f'{self.id} {self.name} can not get rotator current {self.position_type} position, quiting.'
            self.info_callback['stream_1'](inf)
            await self.journal.error(inf)
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            await self.status_error_publish(
                level='critical',
                description=inf,
                plan_runner_quits=True
            )
            return 2

        if self._on_position(current_position=current_pos, target_position=self.position):
            inf = (
                f'{self.id} {self.name} in {self.position_type} position tolerance '
                f'(set {self.position_type} position: {self.position}, '
                f'current {self.position_type} position: {current_pos}), skipping.'
            )
            self.info_callback['stream_1'](inf)
            self.info_callback['stream_5'](f'{self.id}')
            logger.info(inf)
            await self.journal.info(inf)
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0

        _move_ok = await self._move(position=self.position)
        if not _move_ok:
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            inf = f'Can not execute rotator move to position, program stopping'
            logger.error(inf)
            await self.journal.error(inf)
            await self.status_error_publish(
                level='critical',
                description=inf,
                plan_runner_quits=True
            )
            return 2

        wait_slew_ok = await self._wait_to_move(position=self.position)
        if not wait_slew_ok:
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            inf = f'Rotator move get timeout {self.slew_timeout}s, program stopping.'
            logger.error(inf)
            await self.journal.error(inf)
            await self.status_error_publish(
                level='critical',
                description=inf,
                plan_runner_quits=True
            )
            return 2

        logger.info(f'{self.id} {self.name} done')
        self.info_callback['stream_1'](f'{self.id} {self.name} done.')
        self.info_callback['stream_5'](f'{self.id}')
        await self.journal.info(f"{self.id} {self.name} done.")
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
