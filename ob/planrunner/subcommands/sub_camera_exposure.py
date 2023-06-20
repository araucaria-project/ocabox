import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.fits import save_fits_from_array, fits_header, fits_stat
from pyaraucaria.date import julian_to_tuple
from ocaboxapi.formatter import parse_deg_or_dms
from datetime import datetime
import time
import os
import pwd
from typing import Dict, Any, List
import math
import re

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
        self.base_fits_folder = os.path.expanduser(self.telescope.observatory.get_app_cfg('base_fits_dir', f'~/Desktop'))
        self.folder = os.path.join(self.base_fits_folder, f'fits_{self.telescope.id}')
        self.folder_focusing = os.path.join(self.folder, f'focus')
        self.readout_time: float or None = None
        self.readout_time_start: float or None = None
        self.exp_time_start: str or None = None
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)
        self._mk_folder(self.folder)
        self._mk_folder(self.folder_focusing)



    @staticmethod
    def _mk_symlink(target: str, symlink: str):
        os.symlink(src=target, dst=symlink, dir_fd = None)

    def indexing_value(self, value: int, values: List[str]) -> int or str:
        if isinstance(value, int) and isinstance(values, list):
            data = values[value]
        else:
            data = str(value)
        return data

    @staticmethod
    def get_oca_date(jd: float) -> float:
        return jd - 2460000

    @staticmethod
    def add_zero(numb: int):
        return f'{numb:02d}'

    def _provide_target_folder(self) -> str:
        if self.kwargs['type'] == 'focusing':
            lst = os.listdir(self.folder_focusing)
            lst_2 = [int(n) for n in lst if re.fullmatch(r'\d{6}', n)]
            if len(lst_2) == 0:
                num_last = -1
            else:
                num_last = max(lst_2)
            num = num_last + 1
            if os.path.exists(os.path.join(self.folder_focusing, f'{num_last:06d}', f'{self.kwargs["focus_id"]}')):
                target_folder = os.path.join(self.folder_focusing, f'{num_last:06d}')
            else:
                target_folder = os.path.join(self.folder_focusing, f'{num:06d}')
                self._mk_folder(target_folder)
                open(os.path.join(target_folder, f'{self.kwargs["focus_id"]}'), 'a').close()
                if os.path.exists(os.path.join(self.folder_focusing, f'actual')):
                    if os.readlink(os.path.join(self.folder_focusing, f'actual')) is not target_folder:
                        os.remove(os.path.join(self.folder_focusing, f'actual'))
                        self._mk_symlink(target_folder, os.path.join(self.folder_focusing, f'actual'))
                else:
                    self._mk_symlink(target_folder, os.path.join(self.folder_focusing, f'actual'))
        else:
            jd_tuple = julian_to_tuple(math.floor(self.get_julian_date(str(datetime.utcnow())))+0.1)
            mnth = self.add_zero(jd_tuple[1])
            day = self.add_zero(jd_tuple[2])
            simlink_day = f'{jd_tuple[0]}_{mnth}_{day}'
            name = f"{math.floor(self.get_oca_date(self.get_julian_date(str(datetime.utcnow())))):04.0f}"
            target_folder = os.path.join(self.folder, f'{name}')
            if not os.path.exists(target_folder):
                self._mk_folder(target_folder)
            if os.path.exists(os.path.join(self.folder, f'actual')):
                if not os.readlink(os.path.join(self.folder, f'actual')) == target_folder:
                    os.remove(os.path.join(self.folder, f'actual'))
                    self._mk_symlink(target_folder, os.path.join(self.folder, f'actual'))
            else:
                self._mk_symlink(target_folder, os.path.join(self.folder, f'actual'))
            if os.path.exists(os.path.join(self.folder, simlink_day)) is False:
               self._mk_symlink(target_folder, os.path.join(self.folder, simlink_day))
        return target_folder

    async def _camera_aget_imagearray(self) -> List[Any]:
        try:
            array = await self.camera.aget_imagearray()
            return array
        except:
            try:
                logger.warning(f'1-st _camera_aget_imagearray failed')
                array = await self.camera.aget_imagearray()
                return array
            except:
                logger.error(f'2-nd _camera_aget_imagearray failed')

    async def _wait_for_save_fits(self, sub: int, sub_time: float) -> None:
        logger.info(f'_wait_for_save_fits started')
        array = await self._camera_aget_imagearray()
        jd = self.get_julian_date(self.exp_time_start)
        jd_oca = f"{self.get_oca_date(jd):010.5f}"
        logger.info(f'_wait_for_save_fits aget_imagearray done')
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
        OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
        header = fits_header(
            obs_lat=OCA['latitude'],
            parsed_obs_lat=OCA['latitude'],
            obs_lon=OCA['longitude'],
            parsed_obs_lon=OCA['longitude'],
            obs_elev=OCA['elevation'],
            tel_id=str(self.telescope.id),
            utc_now=str(self.exp_time_start.isoformat(sep='T', timespec='auto')),
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
            req_exp=sub_time,
            cam_exp=sub_time,
            ccd_name=str(self.camera.sensorname),
            ccd_temp=self.camera.ccdtemperature,
            ccd_binx=self.camera.binx,
            ccd_biny=self.camera.biny,
            read_mod=str(readoutmode),
            gain=str(gain)
        )
        logger.info(f'_wait_for_save_fits fits_header gather data done')
        file_name = f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}'
        stat = fits_stat(array, size=100, median=False, std=False, min=False, max=False)

        """
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
        f.close()"""

        save_fits_from_array(array,
                             self.target_folder,
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
                                                       mean=round(stat['mean']),
                                                       exp_time=sub_time))

    async def _wait_for_subexposure(self, sub_time: float) -> None:
        logger.info(f'_wait_for_subexposure started')
        # TODO In final version, i.e. on server-side exposures, I would avoid asyncio.sleep and subscibe on imagerady
        #  and camerastate. (exposures may be aborted earlier, no imagerady then)
        if sub_time >= 0.5:
            sub_t = sub_time
        else:
            sub_t = 0.5
        await asyncio.sleep(int(sub_t))
        while True:
            # subexposure_done = self.camera.imageready
            subexposure_done = await self.camera.aget_imageready()
            if subexposure_done is True:
                logger.info(f'_wait_for_subexposure subexposure_done is True')
                break
            await asyncio.sleep(0.1)

    async def arun(self, step_id: str or None = None) -> int:
        logger.info(f'{self.id} started')
        self.target_folder = self._provide_target_folder()
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        sub = self.kwargs["sub_exp"]

        exposure_time = self.kwargs["exp_time"]

        if self.kwargs['type'] == 'skyflat' and exposure_time=='a':
            """
            TODO for filter, time, make test shot on sky with 1s exposure. If value is not what You expect wait
            some time and make test shot again until You don't get expected value of adu, then continue to make
            normal exposure with calculated length of exposure. On another sub, test shot calculation will be
            repeated, up to end. TODO save last value to settings with filter and time and do not take another 
            test shoot again, but calculate from settings.
            """
            logger.info(f'{self.id} auto skyflat procedure started')
            self.info_callback['stream_1'](f'{self.id} auto skyflat procedure started')
            mean_list = []
            test_exposure_time = 1.0
            test_time_interval = 0.0
            test_min_max_adu = (20000, 30000)
            test_min_max_time_exp = (5, 40)
            mean_diff = None
            while True:
                logger.info(f'{self.id} starting test exposure')
                await self.camera.aput_startexposure(test_exposure_time, self.kwargs["light"])
                await self._wait_for_subexposure(test_exposure_time)
                mean = fits_stat(await self.camera.aget_imagearray(), size=100,
                                 median=False, std=False, min=False, max=False)['mean']
                # TODO take zero_level from settings
                zero_level = 290.0
                if mean > zero_level:
                    mean = mean - zero_level
                logger.info(f'{self.id} test_frame time:{test_exposure_time}s mean-zero:{mean}')
                self.info_callback['stream_1'](f'{self.id} test_frame time:{test_exposure_time}s mean-zero:{mean}')
                self.info_callback['exec_json'](self.exec_json(test_exp_mean=mean))
                mean_list.append(mean)
                if len(mean_list) > 1:
                    mean_diff = mean_list[-1] - mean_list[-2]
                mean_min_max = (test_min_max_time_exp[0] * mean, test_min_max_time_exp[1] * mean)

                # Check if should skipp
                if mean_diff is not None:
                    if mean_diff < 0 and mean_min_max[1] < test_min_max_adu[0]:
                        logger.info(f"{self.id} skipped - it's too dark")
                        self.info_callback['stream_1'](f"{self.id} skipped - it's too dark")
                        self.skipped = True
                        self.info_callback['exec_json'](self.exec_json())
                        return 1
                    elif mean_diff > 0 and mean_min_max[0] > test_min_max_adu[1]:
                        logger.info(f"{self.id} skipped - it's too bright")
                        self.info_callback['stream_1'](f"{self.id} skipped - it's too bright")
                        self.skipped = True
                        self.info_callback['exec_json'](self.exec_json())
                        return 1

                # Check if it's ready to calculate exposure time
                if test_min_max_adu[0] - mean_min_max[1] < 0 < test_min_max_adu[1] - mean_min_max[0]:
                    if mean_min_max[0] < test_min_max_adu[0]:
                        exposure_time = test_min_max_adu[0] / mean
                        self.info_callback['stream_1'](f"{self.id} calc_exp_time:{exposure_time},"
                                                       f" expect_adu:{exposure_time * mean}")
                        logger.info(f"{self.id} calc_exp_time:{exposure_time}, expect_adu:{exposure_time * mean}")
                        break
                    else:
                        exposure_time = mean_min_max[0] / mean
                        self.info_callback['stream_1'](f"{self.id} calc_exp_time:{exposure_time},"
                                                       f" expect_adu:{exposure_time * mean}")
                        logger.info(f"{self.id} calc_exp_time:{exposure_time}, expect_adu:{exposure_time * mean}")
                        break
                await asyncio.sleep(test_time_interval)

        logger.info(f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} started')
        self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} started')
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=False,
                                                       exp_saved=False,
                                                       n_exp=sub,
                                                       exp_time=exposure_time))
        self.exp_time_start = datetime.utcnow()
        self.readout_time_start = time.time()
        await self.camera.aput_startexposure(float(exposure_time), self.kwargs["light"])
        await self._wait_for_subexposure(float(exposure_time))
        self.readout_time = time.time() - self.readout_time_start - float(exposure_time)
        logger.info(f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} saving')
        self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} --> saving')
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=True,
                                                       exp_saved=False,
                                                       readout_time=self.readout_time,
                                                       n_exp=sub,
                                                       exp_time=exposure_time))
        await self._wait_for_save_fits(sub, float(exposure_time))
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json(exp_time=exposure_time))
        await asyncio.sleep(0.2)
        return 0
