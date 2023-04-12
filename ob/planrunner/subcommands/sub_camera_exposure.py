import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.fits import save_fits_from_array, fits_header, fits_stat
from pyaraucaria.date import datetime_to_julian
from ocaboxapi.formatter import parse_deg_or_dms
from datetime import datetime
import os
import pwd
from collections import OrderedDict
from typing import Dict, Any

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'camera-exposure', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self.cover = self.telescope.get_covercalibrator()
        self.filter = self.telescope.get_filterwheel()
        self.focuser = self.telescope.get_focuser()
        self.rotator = self.telescope.get_rotator()
        self.kwargs = kwargs
        self.id = id
        self.user = pwd.getpwuid(os.getuid())[0]
        self.folder = f'/home/{self.user}/Desktop/fits_{self.telescope.id}/'
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)
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
        # array = await self.camera.aget_imagearrayvariant()

        jd = datetime_to_julian(str(datetime.utcnow()))
        jd_oca = f"{(jd - 2460000):010.5f}"

        # TODO This OCA should be taken from settings
        OCA = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}

        header = fits_header(
                    obs_lat=OCA['latitude'],
                    parsed_obs_lat=parse_deg_or_dms(OCA['latitude']),
                    obs_lon=OCA['longitude'],
                    parsed_obs_lon=parse_deg_or_dms(OCA['longitude']),
                    obs_elev=OCA['elevation'],
                    tel_id=str(self.telescope.id),
                    utc_now=str(datetime.utcnow()),
                    jd=jd,
                    req_ra=self.kwargs["req_ra"],
                    req_dec=self.kwargs["req_dec"],
                    epoch=self.kwargs["epoch"],
                    tel_ra=self.mount.rightascension,
                    tel_dec=self.mount.declination,
                    tel_alt=self.mount.altitude,
                    tel_az=self.mount.azimuth,
                    focus=self.focuser.position,
                    rotator_pos=self.rotator.position,
                    obs_type=self.kwargs['type'],
                    object=self.kwargs["obj_name"],
                    filter=self.kwargs["filter"],
                    req_exp=self.kwargs["exp_time"],
                    cam_exp=self.kwargs["exp_time"],
                    ccd_name=self.camera.sensorname,
                    ccd_temp=self.camera.ccdtemperature,
                    ccd_binx=self.camera.binx,
                    ccd_biny=self.camera.biny,
                    read_mod=self.camera.readoutmode)

        file_name = f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}'

        # Camra Log
        f = open(f'{self.folder}camera_log.txt', "a")
        f.write(f'Date:{datetime.utcnow()}')
        f.write(f' Type:{self.kwargs["type"]}')
        f.write(f' Object:{self.kwargs["obj_name"]}')
        f.write(f' Filter:{self.kwargs["filter"]}')
        f.write(f' Exp-time:{self.kwargs["exp_time"]}')
        stat = fits_stat(array, median=False, std=False)
        f.write(' Min:')
        f.write(str(stat['min']))
        f.write(' Max:')
        f.write(str(stat['max']))
        f.write(' Mean:')
        f.write(str(stat['mean']))
        f.write(f' File-name:{file_name}')
        f.write('\n')
        f.close()

        save_fits_from_array(array,
                             f'{self.folder}',
                             file_name,
                             header,
                             overwrite=True,
                             dtyp='sideint16')
        logger.debug(f'{self.id} {self.subcommand_name} is done')
        self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} done')
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=True,
                                                       exp_saved=True,
                                                       n_exp=sub))

    async def _wait_for_subexposure(self, sub: int):
        while True:
            await asyncio.sleep(1)
            subexposure_done = self.camera.imageready
            if subexposure_done:
                logger.debug(f'{self.id} {self.subcommand_name} is done --> saving')
                self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} --> saving')
                self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                               exp_done=True,
                                                               exp_saved=False,
                                                               n_exp=sub))
                break

    async def arun(self, step_id: str or None = None) -> int:
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        for sub in range(1, self.kwargs["exp_no"]+1):
            self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} started')
            self.info_callback['exec_json'](self.exec_json(sub_started=True,
                                                           sub_done=False,
                                                           sub_saved=False,
                                                           n_exp=sub))
            await self.camera.aput_startexposure(self.kwargs["exp_time"], self.kwargs["light"])
            await asyncio.sleep(1)
            await self._wait_for_subexposure(sub)
            await asyncio.sleep(1)
            await self._wait_for_save_fits(sub)
        await asyncio.sleep(1)
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0


