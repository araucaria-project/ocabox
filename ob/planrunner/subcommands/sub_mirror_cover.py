import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MirrorCover(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 open: bool, uobi: int, name: str = 'mirror-cover', param: Dict[str, Any] or None = None) -> None:
        self.open = open
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        super().__init__(id=id, info_callback=info_callback, telescope=telescope,
                         name=name, uobi=uobi, param=param)
        self.mount = self.telescope.get_mount('mount')
        self.cover = self.telescope.get_covercalibrator()
        self.info_dict = {'open': self.open}
        self.create_sub_command_string(**self.info_dict)

    async def _wait_for_move(self, expected_status: str):
        while True:
            cover_status = await self.value_proof_get(name='coverstate',
                                                      awaitab=self.cover.aget_coverstate,
                                                      expect_type=bool)
            if str(cover_status) == expected_status:
                break
            await asyncio.sleep(0.5)

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, field='started', value=True)
        inf = f'{self.id} {self.name} started.'
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(inf)
        await self.journal.info(inf)
        cover_status = await self.value_proof_get(name='coverstate',
                                                  awaitab=self.cover.aget_coverstate,
                                                  expect_type=bool)

        # {"3": "success", "1": "off", "2": "warning"})
        if self.open and str(cover_status) == "1":
            inf = f'{self.id} {self.name} opening.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            if self.telescope.id == 'dev':
                pass
            else:
                await self.mount.aput_opencover()
                await self._wait_for_move(expected_status="3")
            inf = f'{self.id} {self.name} opening done.'
            self.info_callback['stream_1'](inf)
            logger.info(inf)
            self.info_callback['stream_5'](f'{self.id}')
            self.done = True
            await self.param['plan_status'].upd_status(id=self.id, field='done', value=True)
            await self.journal.info(inf)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0
        elif not self.open and str(cover_status) == "3":
            inf = f'{self.id} {self.name} closing.'
            self.info_callback['stream_1'](inf)
            await self.journal.debug(inf)
            logger.debug(inf)
            if self.telescope.id == 'dev':
                pass
            else:
                await self.mount.aput_closecover()
                await self._wait_for_move(expected_status="1")
            inf = f'{self.id} {self.name} closing done.'
            logger.info(inf)
            self.done = True
            await self.param['plan_status'].upd_status(id=self.id, field='done', value=True)
            await self.journal.info(inf)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0
        else:
            pass
        inf = f'{self.id} {self.name} skipped.'
        self.skipped = True
        await self.param['plan_status'].upd_status(id=self.id, field='skipped', value=True)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(f'{self.id} skipped')
        await self.journal.debug(inf)
        return 0
