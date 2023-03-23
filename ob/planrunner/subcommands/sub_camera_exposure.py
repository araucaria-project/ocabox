import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.fits import save_fits_from_array
from pyaraucaria.date import datetime_to_julian
from datetime import datetime
import os
import pwd
from os import path

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(SubCommand):

    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.subcommand_name = 'CameraExposure'
        self.telescope = parent.telescope
        self.camera = self.telescope.get_camera('camera')
        self.kwargs = kwargs
        self.id = id
        self.user = pwd.getpwuid(os.getuid())[0]
        self.folder = f'/home/{self.user}/Desktop/fits_test/'
        super().__init__(id=id, parent=parent, subcommand_name=self.subcommand_name, **kwargs)

    async def _wait_for_save_fits(self, sub: int):
        array = await self.camera.aget_imagearray()
        time_now = str(datetime.utcnow())
        jd_oca = f"{(datetime_to_julian(str(datetime.utcnow())) - 2460000):010.5f}"
        header = {"FITS_STD": "beta_1", "TEL": f"{self.telescope.id}", "UT": f"{time_now}"}
        save_fits_from_array(array,
                             f'{self.folder}',
                             f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}',
                             header,
                             overwrite=True)
        logger.debug(f'{self.id} {self.subcommand_name} is done')
        self.info_callback['stream_1'](f'Subexposure {sub}/{self.kwargs["exposure_no"]} done')

    async def _wait_for_subexposure(self, sub: int):
        while True:
            await asyncio.sleep(1)
            subexposure_done = self.camera.imageready
            if subexposure_done:
                logger.debug(f'{self.id} {self.subcommand_name} is done --> saving')
                self.info_callback['stream_1'](f'Subexposure {sub}/{self.kwargs["exposure_no"]} done --> saving')
                break

    async def arun(self, step_id: str or None = None):
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](
            f'Subcommand {self.id} {self.subcommand_name} '
            f'Subexposure - time:{self.kwargs["exposure_time"]} quantity:{self.kwargs["exposure_no"]} started')
        for sub in range(1, self.kwargs["exposure_no"]+1):
            self.info_callback['stream_1'](f'Subexposure {sub}/{self.kwargs["exposure_no"]} started')
            await self.camera.aput_startexposure(self.kwargs["exposure_time"], True)
            await asyncio.sleep(1)
            await self._wait_for_subexposure(sub)
            await asyncio.sleep(1)
            await self._wait_for_save_fits(sub)
        await asyncio.sleep(5)
        self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')


    """
    hdr["FITS_STD"]="BETA1"
    hdr["TEL"]=str(self.parent.active_tel)
    hdr["UT"]=str(self.parent.ut)
    hdr["JD"]=str(self.parent.jd)

    hdr["TEL_RA"]=str(self.parent.mount_ra )
    hdr["TEL_DEC"]=str(self.parent.mount_dec)
    hdr["TEL_ALT"]=str(self.parent.mount_alt)
    hdr["TEL_AZ"]=str(self.parent.mount_az )

    hdr["TYPE"]=self.parent.ob_type
    hdr["OBJECT"]=self.parent.ob_name
    hdr["FILTER"]=self.parent.curent_filter
    hdr["DIT"]=self.parent.dit_exp

    hdr["CCD_NAME"]=str(self.parent.ccd_name)
    hdr["CCD_TEMP"]=str(self.parent.ccd_temp)
    hdr["CCD_BINX"]=str(self.parent.ccd_binx)
    hdr["CCD_BINY"]=str(self.parent.ccd_biny)
    hdr["RAED_MOD"]=str(self.parent.ccd_readmode)


    hdr["FOCUS"]=str(self.parent.focus_value)"""