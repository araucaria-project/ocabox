import asyncio
import logging
from ob.planrunner.subcommand import SubCommand

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MirrorCover(SubCommand):


    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'mirror-cover', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        self.cover = self.telescope.get_covercalibrator()
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

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
        self.info_callback['exec_json'](self.exec_json())
        logger.info(f'{self.id} started')
        cover_status = await self.value_proof_get(name='coverstate',
                                                  awaitab=self.cover.aget_coverstate,
                                                  expect_type=bool)
        if 'open' in self.kwargs.keys():
            # {"3": "success", "1": "off", "2": "warning"})
            if self.kwargs['open']==True and str(cover_status) == "1":
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} opening')
                logger.debug(f'{self.id} opening')
                if self.telescope.id == 'dev':
                    pass
                else:
                    await self.mount.aput_opencover()
                    await self._wait_for_move(expected_status="3")
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                logger.info(f'{self.id} done')
                self.info_callback['stream_5'](f'{self.id}')
                self.done = True
                self.info_callback['exec_json'](self.exec_json())
                return 0
            elif self.kwargs['open']==False and str(cover_status) == "3":
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} closing')
                logger.debug(f'{self.id} closing')
                if self.telescope.id == 'dev':
                    pass
                else:
                    await self.mount.aput_closecover()
                    await self._wait_for_move(expected_status="1")
                logger.info(f'{self.id} done')
                self.done = True
                self.info_callback['exec_json'](self.exec_json())
                return 0
            else:
                pass
        self.skipped = True
        self.info_callback['exec_json'](self.exec_json())
        logger.info(f'{self.id} skipped')
        return 0