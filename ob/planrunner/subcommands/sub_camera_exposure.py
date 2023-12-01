import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.fits import save_fits_from_array, fits_header, fits_stat
from pyaraucaria.date import julian_to_tuple
from datetime import datetime
import time
import os
from typing import Dict, Any, List, Tuple
import math
import re
from serverish.messenger import Messenger, request
from serverish.base.datetime import dt_utcnow_array
from serverish.base.exceptions import MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(SubCommand):

    def __init__(self, id: str, parent: 'Command', seq_data: 'Seq', subcommand_name: str = 'camera-exposure', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self.cover = self.telescope.get_covercalibrator()
        self.filter = self.telescope.get_filterwheel()
        self.focuser = self.telescope.get_focuser()
        self.rotator = self.telescope.get_rotator()
        self.kwargs = kwargs
        self.seq_data = seq_data
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

    def indexing_value(self, value, values):
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

    @property
    def if_autoexposure(self) -> bool:
        if 'auto_exposure' in self.kwargs.keys():
            if self.kwargs['auto_exposure'] == True:
                return True
            else:
                return False
        else:
            return False

    @property
    def subexp_no(self) -> int or None:
        if "sub_exp" in self.kwargs.keys():
            return self.kwargs["sub_exp"]
        else:
            return None

    def array_bits(self, rmmode) -> str:
        if self.telescope.id == 'jk15':
            if rmmode in [3, 5]:
                return 'int32'
        return 'sideint16'

    @property
    def obs_type(self) -> str:
        if self.kwargs['type'] == 'snap':
            return f'test'
        elif self.kwargs['type'] == 'focusing':
            return f'focus'
        elif self.kwargs['type'] in ['flat', 'dark', 'zero']:
            return f'calib'
        else:
            return f'science'

    def _get_today_symlink_name(self) -> str:
        """
        Create name for symlink, name is user-friendly date format YYYY_MM_DD with date when night is started
        @return: Str in format YYYY_MM_DD
        """
        jd_tuple = julian_to_tuple(math.floor(self.get_julian_date(str(datetime.utcnow()))) + 0.1)
        mnth = self.add_zero(jd_tuple[1])
        day = self.add_zero(jd_tuple[2])
        return f'{jd_tuple[0]}_{mnth}_{day}'

    def _get_today_fits_folder_name(self) -> str:
        return f"{math.floor(self.get_oca_date(self.get_julian_date(str(datetime.utcnow())))):04.0f}"

    @property
    def rpc_subject(self) -> str:
        # TODO take from settings
        return f'tic.rpc.{self.telescope.id}.ccd'

    def rpc_data(self, fits_id: str, header: Dict, req: str,
                 file_location: str, mean_points_no_stats: int, dtyp: str, symlink_location: str) -> Dict:
        return {
            'telescope_id': self.telescope.id,
            'ts': dt_utcnow_array(),
            'request': req,
            'fits_id': fits_id,
            'file_location': file_location,
            'dtyp': dtyp,
            'mean_points_no_stats': mean_points_no_stats,
            'symlink_location': symlink_location,
            'header': header}

    async def rpc_request(self, fits_id: str,
                          header: Dict,
                          req: str = 'fits_download',
                          file_location: str = '~/Desktop/fits_dev/test',
                          symlink_location: str = '~/Desktop/fits_dev/test',
                          mean_points_no_stats: int = 100,
                          dtyp: str = 'sideint16',
                          timeout: float = 10):
        logger.info(f'Send rpc {self.rpc_subject}')
        dat, met = await request(subject=self.rpc_subject,
                                 data=self.rpc_data(fits_id=fits_id, header=header,
                                                    file_location=file_location, req=req,
                                                    mean_points_no_stats=mean_points_no_stats,
                                                    dtyp=dtyp, symlink_location=symlink_location),
                                 timeout=timeout)
        logger.debug(f'Data gather: {dat}')
        return dat

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
                target_folder_name = f'{num:06d}'
                target_folder = os.path.join(self.folder_focusing, target_folder_name)
                self._mk_folder(target_folder)
                open(os.path.join(target_folder, f'{self.kwargs["focus_id"]}'), 'a').close()
                if os.path.exists(os.path.join(self.folder_focusing, f'actual')):
                    os.remove(os.path.join(self.folder_focusing, f'actual'))
                self._mk_symlink(target=f'./{target_folder_name}', symlink=os.path.join(self.folder_focusing,
                                                                                        f'actual'))

        elif self.kwargs['type'] == 'snap':
            target_folder = self.folder
        else:
            today_symlink_name = self._get_today_symlink_name()
            today_fits_folder_name = self._get_today_fits_folder_name()
            target_folder = os.path.join(self.folder, f'{today_fits_folder_name}')

            # Create today fits folder name (last 4 digits of julian date)
            if not os.path.exists(target_folder):
                self._mk_folder(target_folder)

            # Create actual symlink to today fits folder
            if os.path.exists(os.path.join(self.folder, f'actual')):
                if not os.readlink(os.path.join(self.folder, f'actual')) == target_folder:
                    os.remove(os.path.join(self.folder, f'actual'))
                    self._mk_symlink(target=f'./{today_fits_folder_name}', symlink=os.path.join(self.folder, f'actual'))
            else:
                self._mk_symlink(target=f'./{today_fits_folder_name}', symlink=os.path.join(self.folder, f'actual'))

            # Create date friendly format symlink to today fits folder
            if not os.path.exists(os.path.join(self.folder, today_symlink_name)):
                self._mk_symlink(target=f'./{today_fits_folder_name}', symlink=os.path.join(self.folder,
                                                                                            today_symlink_name))

        return target_folder

    async def _wait_for_save_fits(self, sub: int, sub_time: float) -> bool:
        logger.info(f'_wait_for_save_fits started')

        jd = self.get_julian_date(self.exp_time_start)
        jd_oca = f"{self.get_oca_date(jd):010.5f}"
        logger.info(f'_wait_for_save_fits aget_imagearray done')
        gainmode = await self.value_proof_get(name='fitsh_cam_gain',
                                              awaitab=self.camera.aget_gain,
                                              expect_type=int)
        readoutmode = await self.value_proof_get(name='fitsh_cam_rm',
                                                 awaitab=self.camera.aget_readoutmode,
                                                 expect_type=int)
        filter = await self.value_proof_get(name='fitsh_filter',
                                            awaitab=self.filter.aget_position,
                                            expect_type=int)
        filters = await self.value_proof_get(name='fitsh_filters',
                                             awaitab=self.filter.aget_names,
                                             expect_type=dict)

        try:
            inv_f_map = {v: k for k, v in filters.items()}
            filter_str = inv_f_map[filter]
        except KeyError:
            filter_str = str(self.kwargs["filter"])

        if self.kwargs["req_ra"] is None:
            req_ra = ''
        else:
            req_ra = self.kwargs["req_ra"]

        if self.kwargs["req_dec"] is None:
            req_dec = ''
        else:
            req_dec = self.kwargs["req_dec"]

        # TODO This OCA should be taken from settings
        OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
        header = fits_header(
            obs_lat=OCA['latitude'],
            obs_lon=OCA['longitude'],
            obs_elev=OCA['elevation'],
            tel_id=str(self.telescope.id),
            utc_now=str(self.exp_time_start.isoformat(sep='T', timespec='auto')),
            jd=jd,
            req_ra=req_ra,
            req_dec=req_dec,
            epoch=self.kwargs["epoch"],
            tel_ra=await self.value_proof_get(name='fitsh_tel_ra', awaitab=self.mount.aget_ra, expect_type=float),
            tel_dec=await self.value_proof_get(name='fitsh_tel_dec', awaitab=self.mount.aget_dec, expect_type=float),
            tel_alt=await self.value_proof_get(name='fitsh_tel_alt', awaitab=self.mount.aget_alt, expect_type=float),
            tel_az=await self.value_proof_get(name='fitsh_tel_az', awaitab=self.mount.aget_az, expect_type=float),
            focus=await self.value_proof_get(name='fitsh_focus_pos',
                                             awaitab=self.focuser.aget_position,
                                             expect_type=int),
            rotator_pos=await self.value_proof_get(name='fitsh_rot_pos',
                                                   awaitab=self.rotator.aget_position,
                                                   expect_type=float),
            observer=str(self.kwargs['observer']),
            image_type=str(self.kwargs['type']),
            obs_type=self.obs_type,
            object=str(self.kwargs["obj_name"]),
            n_loops=self.kwargs["exp_no"],
            loop=sub,
            filter=filter_str,
            exp_time=sub_time,
            instrume_name=str(await self.value_proof_get(name='fitsh_cam_sens_name',
                                                         awaitab=self.camera.aget_sensorname,
                                                         expect_type=str)),
            ccd_temp=await self.value_proof_get(name='fitsh_cam_temp',
                                                awaitab=self.camera.aget_ccdtemperature,
                                                expect_type=float),
            binx=await self.value_proof_get(name='fitsh_cam_binx',
                                            awaitab=self.camera.aget_binx,
                                            expect_type=int),
            biny=await self.value_proof_get(name='fitsh_cam_biny',
                                            awaitab=self.camera.aget_biny,
                                            expect_type=int),
            read_mod=readoutmode,
            gain_mod=gainmode
        )
        logger.info(f'_wait_for_save_fits fits_header gather data done')
        if self.kwargs['type'] == 'snap':
            file_name = f'snap'
        else:
            file_name = f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}'

        # array = await self.value_proof_get(name='fits_get_array',
        #                                    awaitab=self.camera.aget_imagearray, expect_type=list)
        #stat = fits_stat(array, size=100, median=False, std=False, min=False, max=False)
        #save_fits_from_array(array, self.target_folder, file_name, header, overwrite=True,
        #                     dtyp=self.array_bits(rmmode=readoutmode))
        try:
            # Add file_location, dtyp, symlink_location parameters on no-test
            dat = await self.rpc_request(fits_id=file_name, header=header)
        except (MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout):
            logger.error(f'Nats rpc guider msg can not reach responder')
            self.info_callback['stream_1'](f'ERROR: can not reach ofp download.')
            return False
        if dat:
            try:
                if dat['response'] == 'fits_saved':
                    logger.info(f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} done')
                    self.info_callback['stream_1'](f'{self.id} exp:{sub}/{self.kwargs["exp_no"]} done')
                    self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                                   exp_done=True,
                                                                   exp_saved=True,
                                                                   n_exp=sub,
                                                                   mean=round(dat['param']['mean']),
                                                                   exp_time=sub_time))
                    return True
                else:
                    logger.error(f'Wrong rpc response, no fits_saved.')
                    self.info_callback['stream_1'](f'ERROR: wrong rpc response.')
                    return False
            except KeyError:
                logger.error(f'Wrong rpc response, KeyError')
                self.info_callback['stream_1'](f'ERROR: wrong rpc response.')
                return False
        else:
            logger.error(f'Wrong rpc response')
            self.info_callback['stream_1'](f'ERROR: wrong rpc response, dat is None.')
            return False

    async def _wait_for_subexposure(self, sub_time: float) -> None:
        logger.info(f'_wait_for_subexposure started')
        # TODO In final version, i.e. on server-side exposures, I would avoid asyncio.sleep and subscibe on imagerady
        #  and camerastate. (exposures may be aborted earlier, no imagerady then)
        if sub_time >= 0.6:
            sub_t = sub_time
        else:
            sub_t = 1.0
        await asyncio.sleep(float(sub_t))
        while True:
            subexposure_done = await self.value_proof_get(name='wait_subexp',
                                                          awaitab=self.camera.aget_imageready,
                                                          expect_type=bool)
            if subexposure_done is True:
                logger.info(f'_wait_for_subexposure subexposure_done is True')
                break
            await asyncio.sleep(0.1)

    async def get_array_autoexp(self, test_exp_time: float) -> List:
        #if self.telescope.id == 'dev':
        #    test_mode = True
        #else:
        #    test_mode = False
        #if not test_mode:
        await self.camera.aput_startexposure(test_exp_time, self.kwargs["light"])
        await self._wait_for_subexposure(test_exp_time)
        return await self.value_proof_get(name='autoexp_get_array',
                                         awaitab=self.camera.aget_imagearray,
                                         expect_type=list)
        #else:
        #    with open(os.path.expanduser('~/.oca/camera_sim.txt'), 'r') as f:
        #        arr = json.load(f)
        #        f.close()
        #        return arr

    async def _autoexposure_exec(self) -> Tuple[float, bool]:
        """
        TODO for filter, time, make test shot on sky with 1s exposure. If value is not what You expect wait
        some time and make test shot again until You don't get expected value of adu, then continue to make
        normal exposure with calculated length of exposure. On another sub, test shot calculation will be
        repeated, up to end.
        """
        logger.info(f'{self.id} auto skyflat procedure started')
        self.info_callback['stream_1'](f'{self.id} auto skyflat procedure started')
        mean_list = []
        mean_diff = None
        auto_exp_sub_no = 0

        # TODO take all values from settings (for zero_level maybe make some zero?)
        test_exposure_time = 1.0 # Test exposure time
        test_time_interval = 1 # Test interval
        test_min_max_adu = (20000, 25000) # Accepted flat adu range
        test_min_max_time_exp = (2, 30) # Accepted flat time range
        zero_level = 290.0 # Zero mean
        evening_factor = 1.11 # Evening factor to set comparable values from morning and evening

        # Get inf if it is evening or morning and set ev_factor
        if datetime.utcnow().hour > 14:
            evening = True
            ev_fact = evening_factor
        else:
            evening = False
            ev_fact = 1
        while True:
            logger.info(f'{self.id} starting test exposure')
            auto_exp_sub_no += 1
            #self.info_callback['exec_json'](self.exec_json(auto_exp_start=True,
            #                                               auto_exp_finnished=False,
            #                                               auto_exp_sub_no=auto_exp_sub_no,
            #                                               auto_exp_time=test_exposure_time))
            # Make exposure
            #arr = await self.get_array_autoexp(test_exp_time=test_exposure_time)
            # Calculate mean from exposure (plus some info)
            #mean = fits_stat(arr, size=100, median=False, std=False, min=False, max=False)['mean']

            await self.camera.aput_startexposure(test_exposure_time, self.kwargs["light"])
            await self._wait_for_subexposure(test_exposure_time)

            try:
                dat = await self.rpc_request(fits_id=f'{round((time.time())*10)}'[-7:],
                                             header={}, req='stats_only')
            except (MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout):
                logger.error(f'Nats rpc guider msg can not reach responder')
                self.info_callback['stream_1'](f'ERROR: can not reach ofp download.')
                return 0, True
            if dat:
                try:
                    if dat['response'] == 'stats_done':
                        mean = dat['param']['mean']
                    else:
                        logger.error(f'Wrong rpc response.')
                        self.info_callback['stream_1'](f'ERROR: wrong rpc response, no stats_done.')
                        return 0, True
                except KeyError:
                    logger.error(f'Wrong rpc response, key error')
                    self.info_callback['stream_1'](f'ERROR: wrong rpc response, key error.')
                    return 0, True
            else:
                logger.error(f'Wrong rpc response')
                self.info_callback['stream_1'](f'ERROR: wrong rpc response, dat is None.')
                return 0, True

            self.info_callback['exec_json'](self.exec_json(auto_exp_start=True,
                                                           auto_exp_finnished=True,
                                                           auto_exp_sub_no=auto_exp_sub_no,
                                                           auto_exp_time=test_exposure_time))

            # Substract zero from mean and add to mean_list (plus some info)
            if mean > zero_level:
                mean = mean - zero_level
            else:
                mean = 1.0
            mean_list.append(mean)
            logger.info(f'{self.id} Test frame mean:{round(mean, 2)}'
                        f' range:[{round(test_min_max_adu[0]/test_min_max_time_exp[1], 2)}-'
                        f'{round(test_min_max_adu[1]/test_min_max_time_exp[0], 2)}]')
            self.info_callback['stream_1'](f'{self.id} Test frame mean:{round(mean, 2)}'
                        f' range:[{round(test_min_max_adu[0]/test_min_max_time_exp[1], 2)}-'
                        f'{round(test_min_max_adu[1]/test_min_max_time_exp[0], 2)}]')
            self.info_callback['exec_json'](self.exec_json(
                test_exp_mean=mean,
                expected_mean_min=round(test_min_max_adu[0]/test_min_max_time_exp[1]),
                expected_mean_max=round(test_min_max_adu[1]/test_min_max_time_exp[0])))

            # Calculate mean diff from last two steps
            if len(mean_list) > 1:
                mean_diff = mean_list[-1] - mean_list[-2]

            # Calculate mean range times minimal and maximal accepted exposure time
            mean_min_max = (test_min_max_time_exp[0] * mean, test_min_max_time_exp[1] * mean)

            # Check if it should skipp this filter for good
            if mean_diff is not None:
                # Evening
                if evening and mean_diff < 0 and mean_min_max[1] < test_min_max_adu[0]:
                    logger.info(f"{self.id} skipped - it's too dark")
                    self.info_callback['stream_1'](f"{self.id} skipped - it's too dark")
                    self.skipped = True
                    self.info_callback['exec_json'](self.exec_json())
                    self.seq_data.skip = True
                    return 0, True
                # Morning
                elif not evening and mean_diff > 0 and mean_min_max[0] > test_min_max_adu[1]:
                    logger.info(f"{self.id} skipped - it's too bright")
                    self.info_callback['stream_1'](f"{self.id} skipped - it's too bright")
                    self.skipped = True
                    self.info_callback['exec_json'](self.exec_json())
                    self.seq_data.skip = True
                    return 0, True

            # Try to calculate exposure time, if fail next loop starts
            if test_min_max_adu[0] - mean_min_max[1] < 0 < test_min_max_adu[1] - mean_min_max[0]:
                if mean_min_max[0] < test_min_max_adu[0]:
                    exposure_time = (test_min_max_adu[0] / mean) * ev_fact
                    self.info_callback['stream_1'](f"{self.id} calc_exp_time:{round(exposure_time, 1)},"
                                                   f" expect_adu:{round(exposure_time * mean, 1)}")
                    logger.info(f"{self.id} calc_exp_time:{round(exposure_time, 1)},"
                                f" expect_adu:{round(exposure_time * mean, 1)}")
                    return exposure_time, False
                else:
                    exposure_time = (mean_min_max[0] / mean) * ev_fact
                    self.info_callback['stream_1'](f"{self.id} calc_exp_time:{round(exposure_time, 1)},"
                                                   f" expect_adu:{round(exposure_time * mean, 1)}")
                    logger.info(f"{self.id} calc_exp_time:{round(exposure_time, 1)},"
                                f" expect_adu:{round(exposure_time * mean, 1)}")
                    return exposure_time, False
            await asyncio.sleep(test_time_interval)


    async def arun(self, step_id: str or None = None) -> int:

        self.started = True
        if self.seq_data.skip:
            self.skipped = True
            if 'sub_exp' in self.kwargs.keys() and 'exp_no' in self.kwargs.keys():
                if self.kwargs['sub_exp'] == self.kwargs['exp_no']:
                    self.seq_data.skip = False
            return 0
        logger.info(f'{self.id} started')
        self.target_folder = self._provide_target_folder()

        exposure_time = self.seq_data.exp_time

        if self.if_autoexposure:
            exposure_time, _exit = await self._autoexposure_exec()
            if _exit:
                return 0

        logger.info(f'{self.id} exp:{self.subexp_no}/{self.kwargs["exp_no"]} started')
        self.info_callback['stream_1'](f'{self.id} exp:{self.subexp_no}/{self.kwargs["exp_no"]} started')
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=False,
                                                       exp_saved=False,
                                                       n_exp=self.subexp_no,
                                                       exp_time=float(exposure_time)))
        self.exp_time_start = datetime.utcnow()
        self.readout_time_start = time.time()
        await self.camera.aput_startexposure(float(exposure_time), self.kwargs["light"])
        await self._wait_for_subexposure(float(exposure_time))
        self.readout_time = time.time() - self.readout_time_start - float(exposure_time)
        logger.info(f'{self.id} exp:{self.subexp_no}/{self.kwargs["exp_no"]} saving')
        self.info_callback['stream_1'](f'{self.id} exp:{self.subexp_no}/{self.kwargs["exp_no"]} --> saving')
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=True,
                                                       exp_saved=False,
                                                       readout_time=self.readout_time,
                                                       n_exp=self.subexp_no,
                                                       exp_time=float(exposure_time)))
        wff = await self._wait_for_save_fits(sub=self.subexp_no, sub_time=float(exposure_time))
        if not wff:
            return 2
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json(exp_time=float(exposure_time)))
        await asyncio.sleep(0.2)
        return 0
