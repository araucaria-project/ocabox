import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.fits import save_fits_from_array
from pyaraucaria.date import datetime_to_julian
from datetime import datetime
import os
import pwd
from collections import OrderedDict

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'camera exposure', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self.cover = self.telescope.get_covercalibrator()
        self.filter = self.telescope.get_filterwheel()
        self.focuser = self.telescope.get_focuser()
        self.kwargs = kwargs
        self.id = id
        self.user = pwd.getpwuid(os.getuid())[0]
        self.folder = f'/home/{self.user}/Desktop/fits_{self.telescope.id}/'
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name, **kwargs)
        self._mk_folder()

    def _mk_folder(self):
            lst = os.listdir(f'/home/{self.user}/Desktop/')
            if f'fits_{self.telescope.id}' not in lst:
                try:
                    os.mkdir(self.folder)
                except Exception as e:
                    logger.warning(
                        f'Folder creation failed, please make folder /home/{self.user}/Desktop/fits_{self.telescope.id}')

    async def _wait_for_save_fits(self, sub: int):
        array = await self.camera.aget_imagearray()
        time_now = str(datetime.utcnow())
        jd = datetime_to_julian(str(datetime.utcnow()))
        jd_oca = f"{(jd - 2460000):010.5f}"
        if self.kwargs['type'] == 'light':
            typ = f"science"
        else:
            typ = self.kwargs['type']
        header = OrderedDict({
            "FITS_STD": "BETA1",
            "TEL": str(self.telescope.id),
            "UT": str(time_now),
            "JD": str(jd),
            "TEL_RA": str(self.mount.rightascension),
            "TEL_DEC": str(self.mount.declination),
            "TEL_ALT": str(self.mount.altitude),
            "TEL_AZ": str(self.mount.azimuth),
            "TYPE": f"{typ}",
            "OBJECT": str(self.kwargs["obj_name"]),
            "FILTER": str(self.filter.position),
            "DIT": "",
            "CCD_NAME": str(self.camera.name),
            "CCD_TEMP": str(self.camera.ccdtemperature),
            "CCD_BINX": str(self.camera.binx),
            "CCD_BINY": str(self.camera.biny),
            "READ_MOD": str(self.camera.readoutmode),
            "FOCUS": str(self.focuser.position)
        })
        save_fits_from_array(array,
                             f'{self.folder}',
                             f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}',
                             header,
                             overwrite=True)
        logger.debug(f'{self.id} {self.subcommand_name} is done')
        self.info_callback['stream_1'](f'Subexp {sub}/{self.kwargs["exp_no"]} done')

    async def _wait_for_subexposure(self, sub: int):
        while True:
            await asyncio.sleep(1)
            subexposure_done = self.camera.imageready
            if subexposure_done:
                logger.debug(f'{self.id} {self.subcommand_name} is done --> saving')
                self.info_callback['stream_1'](f'Subexp {sub}/{self.kwargs["exp_no"]} --> saving')
                break

    async def _wait_for_cover(self):
        wait = 0
        while True:
            await asyncio.sleep(1)
            wait += 1
            if wait > 10:
                break
            """
            # TODO cover state not working - maybe only time wait
            cover_status = self.cover.coverstate
            if cover_status == 3:
                logger.debug(f'Telescope cover opened')
                self.info_callback['stream_1'](f'Telescope cover is opened')
                break"""


    async def arun(self, step_id: str or None = None) -> int:
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        if self.kwargs["type"] in ['light', 'flat']:
            self.info_callback['stream_1'](f'Opening cover')
            logger.debug(f'Opening cover')
            if self.telescope.id == 'dev':
                await self.cover.aput_opencover_dev()
            else:
                await self.mount.aput_opencover()
            await self._wait_for_cover()
        elif self.kwargs["type"] in ['dark', 'zero']:
            self.info_callback['stream_1'](f'Closing cover')
            logger.debug(f'Closing cover')
            if self.telescope.id == 'dev':
                await self.cover.aput_closecover_dev()
            else:
                await self.mount.aput_closecover()
            await self._wait_for_cover()
        else:
            self.info_callback['stream_1'](f'No exposure type, skipping')
            logger.debug(f'No exposure type, skipping')
            return 1
        self.info_callback['stream_1'](
            f'{self.id} {self.subcommand_name} {self.kwargs["type"]}'
            f' time:{self.kwargs["exp_time"]} number:{self.kwargs["exp_no"]} started')
        for sub in range(1, self.kwargs["exp_no"]+1):
            self.info_callback['stream_1'](f'Subexp {sub}/{self.kwargs["exp_no"]} started')
            await self.camera.aput_startexposure(self.kwargs["exp_time"], self.kwargs["light"])
            await asyncio.sleep(1)
            await self._wait_for_subexposure(sub)
            await asyncio.sleep(1)
            await self._wait_for_save_fits(sub)
        await asyncio.sleep(5)
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        return 0


