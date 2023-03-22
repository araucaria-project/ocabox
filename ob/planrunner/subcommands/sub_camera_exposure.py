import asyncio
import logging
from ob.planrunner.subcommand import SubCommand


log = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(SubCommand):

    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.subcommand_name = 'CameraExposure'
        self.telescope = parent.telescope
        self.camera = self.telescope.get_camera('camera')
        self.kwargs = kwargs
        self.id = id
        super().__init__(id=id, parent=parent, subcommand_name=self.subcommand_name, **kwargs)

    async def _wait_for_subexposure(self, sub: int):
        while True:
            await asyncio.sleep(1)
            subexposure_done = self.camera.imageready
            if subexposure_done:
                log.debug(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'Subexposure {sub}/{self.kwargs["exposure_no"]} done')
                break

    async def arun(self, step_id: str or None = None):
        log.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](
            f'Subcommand {self.id} {self.subcommand_name} '
            f'Subexposure - time:{self.kwargs["exposure_time"]} quantity:{self.kwargs["exposure_no"]} started')
        for sub in range(1, self.kwargs["exposure_no"]+1):
            self.info_callback['stream_1'](f'Subexposure {sub}/{self.kwargs["exposure_no"]} started')
            await self.camera.aput_startexposure(self.kwargs["exposure_time"], True)
            await asyncio.sleep(1)
            await self._wait_for_subexposure(sub)
            # TODO FITS: get, convert, add header and save to location
        await asyncio.sleep(5)
        self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')