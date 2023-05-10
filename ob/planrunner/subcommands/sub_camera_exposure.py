import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.fits import save_fits_from_array, fits_header, fits_stat
from pyaraucaria.date import datetime_to_julian
from ocaboxapi.formatter import parse_deg_or_dms
from datetime import datetime
import time
import os
import pwd
from typing import Dict, Any, List

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'camera-exposure', **kwargs) -> None:
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)
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
        # TODO: This folder should be taken from settings
        # self.base_fits_folder = os.path.expanduser(self.observatory.get_app_cfg('base_fits_dir', f'~/Desktop'))
        self.base_fits_folder = os.path.expanduser(self.telescope.observatory.get_app_cfg('base_fits_dir', f'~/Desktop'))
        self.folder = os.path.join(self.base_fits_folder, f'fits_{self.telescope.id}')
        self.readout_time: float or None = None
        self.readout_time_start: float or None = None
        self.exp_time_start: str or None = None
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)
        self._mk_folder()

    def _mk_folder(self):
        if not os.path.exists(self.folder):
            try:
                os.mkdir(self.folder)
                logger.info(f'Creating folder {self.folder}')
            except Exception as e:
                logger.warning(
                    f'Folder creation failed, please create folder {self.folder} manually '
                    f'or adjust config key "app.base_fits_dir". Error: {e}'
                )
        else:
            logger.debug(f'Folder {self.folder} exist')

    def indexing_value(self, value: int, values: List[str]) -> int or str:
        if isinstance(value, int) and isinstance(values, list):
            data = values[value]
        else:
            data = str(value)
        return data

    """async def get_value_array(self):
        # Not implemented yet
        while True:
            array = await self.camera.aget_imagearray()
            if isinstance(array, list):
                return array
            await asyncio.sleep(0.1)"""

    async def _wait_for_save_fits(self, sub: int) -> None:

        array = await self.camera.aget_imagearray()
        jd = datetime_to_julian(self.exp_time_start)
        jd_oca = f"{(jd - 2460000):010.5f}"

        if self.telescope.id == 'dev':
            gain = 'unknown'
            readoutmode = 'unknown'
        else:

            gains = self.camera.gains
            readoutmodes = self.camera.readoutmodes
            # offsets = await self.camera.aget_offsets()
            gain = self.camera.gain
            readoutmode = self.camera.readoutmode
            # offset = await self.camera.aget_offset()

            gain = self.indexing_value(gain, gains)
            readoutmode = self.indexing_value(readoutmode, readoutmodes)
            # offset = indexing_value(offset, offsets)

        # TODO This OCA should be taken from settings
        OCA = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}
        header = fits_header(
            obs_lat=OCA['latitude'],
            parsed_obs_lat=parse_deg_or_dms(OCA['latitude']),
            obs_lon=OCA['longitude'],
            parsed_obs_lon=parse_deg_or_dms(OCA['longitude']),
            obs_elev=OCA['elevation'],
            tel_id=str(self.telescope.id),
            utc_now=str(self.exp_time_start),
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
            obs_type=str(self.kwargs['type']),
            object=str(self.kwargs["obj_name"]),
            filter=str(self.kwargs["filter"]),
            req_exp=self.kwargs["exp_time"],
            cam_exp=self.kwargs["exp_time"],
            ccd_name=str(self.camera.sensorname),
            ccd_temp=self.camera.ccdtemperature,
            ccd_binx=self.camera.binx,
            ccd_biny=self.camera.biny,
            read_mod=str(readoutmode),
            gain=str(gain)
        )

        file_name = f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}'
        stat = fits_stat(array, size=100, median=False, std=False)


        # Camra Log
        f = open(os.path.join(self.folder, 'camera_log.txt'), "a")
        f.write(f'Date:{datetime.utcnow()}')
        f.write(f' Type:{self.kwargs["type"]}')
        f.write(f' n_exp/n_exp_req:{sub}/{self.kwargs["exp_no"]}')
        f.write(f' Exp-time:{self.kwargs["exp_time"]}')
        f.write(f' Object:{self.kwargs["obj_name"]}')
        f.write(f' Filter:{self.kwargs["filter"]}')

        f.write(' Min:')
        f.write(str(stat['min']))
        f.write(' Max:')
        f.write(str(stat['max']))
        f.write(' Mean:')
        f.write(str(round(stat['mean'])))
        f.write(f' File-name:{file_name}')
        f.write('\n')
        f.close()

        save_fits_from_array(array,
                             self.folder,
                             file_name,
                             header,
                             overwrite=True,
                             dtyp='sideint16')
        logger.info(f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} done')
        self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} done')
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=True,
                                                       exp_saved=True,
                                                       n_exp=sub,
                                                       mean=round(stat['mean'])
                                                       ))

    async def _wait_for_subexposure(self, sub: int, sub_time: float) -> None:

        if sub_time >= 0.5:
            sub_t = sub_time
        else:
            sub_t = 0.5
        await asyncio.sleep(sub_t)

        while True:
            subexposure_done = self.camera.imageready
            if subexposure_done is True:
                self.readout_time = time.time() - self.readout_time_start - self.kwargs["exp_time"]
                logger.info(f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} saving')
                self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} --> saving')
                self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                               exp_done=True,
                                                               exp_saved=False,
                                                               readout_time=self.readout_time,
                                                               n_exp=sub))
                break
            await asyncio.sleep(0.5)

    async def arun(self, step_id: str or None = None) -> int:
        logger.info(f'{self.id} started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        for sub in range(1, self.kwargs["exp_no"] + 1):
            logger.info(f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} started')
            self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} started')
            self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                           exp_done=False,
                                                           exp_saved=False,
                                                           n_exp=sub))
            self.readout_time_start = time.time()
            self.exp_time_start = str(datetime.utcnow())
            await self.camera.aput_startexposure(self.kwargs["exp_time"], self.kwargs["light"])
            await self._wait_for_subexposure(sub, self.kwargs["exp_time"])
            await self._wait_for_save_fits(sub)
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        await asyncio.sleep(1)
        return 0


