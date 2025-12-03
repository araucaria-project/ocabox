import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from typing import Callable, Dict, Any, Optional
from ob.planrunner.status import PlanStatusEnum


logger = logging.getLogger(__name__.rsplit('.')[-1])


class MirrorCover(BaseSubCommand):

    def __init__(
            self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
            open: bool, uobi: int, name: str = 'mirror-cover', param: Optional[Dict[str, Any]] = None) -> None:

        self.open = open
        self.ra_now: Optional[str] = None
        self.dec_now: Optional[str] = None
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi, param=param)
        self.cover = self.telescope.get_covercalibrator()
        self.info_dict = {'open': self.open}
        self.create_sub_command_string(**self.info_dict)

    async def _wait_for_move(self, expected_status: str):
        while True:
            cover_status = await self.value_proof_get(
                name='coverstate', awaitab=self.cover.aget_coverstate, expect_type=bool
            )
            if str(cover_status) == expected_status:
                break
            await asyncio.sleep(0.5)

    async def arun(self, step_id: Optional[str] = None) -> int:
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        inf = f'{self.id} {self.name} started.'
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(inf)
        await self.journal.info(inf)
        cover_status = await self.value_proof_get(
            name='coverstate', awaitab=self.cover.aget_coverstate, expect_type=bool
        )
        if self.open and str(cover_status) == "1":
            inf = f'{self.id} {self.name} opening mirror cover...'
            self.info_callback['stream_1'](inf)
            await self.journal.info(inf)
            logger.info(inf)
            if self.telescope.id == 'dev':
                pass
            else:
                oc1 = await self.proof_put(awaitab=self.cover.aput_opencover)
                if not oc1:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not open cover, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    await self.status_error_publish(
                        level='critical',
                        description=inf,
                        plan_runner_quits=True
                    )
                    return 2
                await self._wait_for_move(expected_status="3")
            inf = f'{self.id} {self.name} opening mirror cover done'
            self.info_callback['stream_1'](inf)
            logger.info(inf)
            self.info_callback['stream_5'](f'{self.id}')
            self.done = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
            await self.journal.info(inf)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0
        elif not self.open and str(cover_status) == "3":
            inf = f'{self.id} {self.name} closing cover...'
            self.info_callback['stream_1'](inf)
            await self.journal.info(inf)
            logger.info(inf)
            if self.telescope.id == 'dev':
                pass
            else:
                oc1 = await self.proof_put(awaitab=self.cover.aput_closecover)
                if not oc1:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not close cover, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    await self.status_error_publish(
                        level='critical',
                        description=inf,
                        plan_runner_quits=True
                    )
                    return 2
                await self._wait_for_move(expected_status="1")
            inf = f'{self.id} {self.name} closing mirror cover done'
            logger.info(inf)
            self.done = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
            await self.journal.info(inf)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0
        else:
            pass
        inf = f'{self.id} {self.name} skipped.'
        self.skipped = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(f'{self.id} skipped')
        await self.journal.debug(inf)
        return 0
