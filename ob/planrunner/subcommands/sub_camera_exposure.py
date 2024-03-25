import asyncio
import logging
from typing import Callable, Dict, Any
from ob.planrunner.base_subcommand import BaseSubCommand
from pyaraucaria.fits import fits_header
from pyaraucaria.date import julian_to_tuple
import datetime
import time
import os
from typing import Dict, List, Tuple
import math
import re
from serverish.messenger import request
from serverish.base.datetime import dt_utcnow_array
from serverish.base.exceptions import MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout

from ob.planrunner.status import PlanStatusEnum

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable], seq_data: 'Seq', uobi: int,
                 type: str, filter: str, light: bool, sub_exp: int, exp_no: int, auto_exposure: bool,
                 epoch: str, observer: str, obj_name: str, req_ra: float or None = None, req_dec: float or None = None,
                 name: str = 'camera-exposure', param: Dict[str, Any] or None = None) -> None:

        self.seq_data = seq_data
        self.type = type
        self.filter = filter
        self.light = light
        self.sub_exp = sub_exp
        self.exp_no = exp_no
        self.auto_exposure = auto_exposure
        self.epoch = epoch
        self.observer = observer
        self.obj_name = obj_name
        self.req_ra = req_ra
        self.req_dec = req_dec
        self.target_folder: str or None = None
        self.symlinks: List = []
        self.readout_time: float or None = None
        self.readout_time_start: float or None = None
        self.exp_time_start: str or None = None
        self.fits_file_name: str or None = None
        super().__init__(id=id, info_callback=info_callback,
                         telescope=telescope, name=name, uobi=uobi, param=param)
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self.cover = self.telescope.get_covercalibrator()
        self.filter_wheel = self.telescope.get_filterwheel()
        self.focuser = self.telescope.get_focuser()
        self.rotator = self.telescope.get_rotator()

        self.info_dict = {
            'type': self.type,
            'filter': filter,
            'light': light,
            'sub_exp': sub_exp,
            'exp_no': exp_no,
            'auto_exposure': auto_exposure,
            'epoch': epoch,
            'observer': observer,
            'obj_name': obj_name,
            'req_ra': req_ra,
            'req_dec': req_dec}
        self.create_sub_command_string(**self.info_dict)

    @staticmethod
    def get_oca_date(jd: float) -> float:
        return jd - 2460000

    @staticmethod
    def add_zero(numb: int):
        return f'{numb:02d}'

    def array_bits(self, rmmode) -> str:
        # TODO Take from settings
        if self.telescope.id == 'jk15':
            if rmmode in [3, 5]:
                return 'int32'
        return 'sideint16'

    @property
    def obs_type(self) -> str:
        if self.type == 'snap':
            return f'test'
        elif self.type == 'focusing':
            return f'focus'
        elif self.type in ['flat', 'dark', 'zero']:
            return f'calib'
        else:
            return f'science'

    def _get_today_symlink_name(self) -> str:
        """
        Create name for symlink, name is user-friendly date format YYYY_MM_DD with date when night is started
        @return: Str in format YYYY_MM_DD
        """
        jd_tuple = julian_to_tuple(math.floor(self.get_julian_date(str(datetime.datetime.utcnow()))) + 0.1)
        mnth = self.add_zero(jd_tuple[1])
        day = self.add_zero(jd_tuple[2])
        return f'{jd_tuple[0]}_{mnth}_{day}'

    def _get_today_fits_folder_name(self) -> str:
        return f"{math.floor(self.get_oca_date(self.get_julian_date(str(datetime.datetime.utcnow())))):04.0f}"

    def _get_fits_file_name(self):
        if self.type == 'snap':
            self.fits_file_name = f'snap'
        else:
            jd = self.get_julian_date(self.exp_time_start)
            jd_oca = f"{self.get_oca_date(jd):010.5f}"
            self.fits_file_name = f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}'

    @property
    def rpc_subject(self) -> str:
        cfg = self.telescope.observatory.get_app_cfg('nats_subject')
        return f"{cfg['rpc_root']}.{self.telescope.id}.{cfg['service_name']['download']}"

    def rpc_data(self, fits_id: str, header: Dict, req: str,
                mean_points_no_stats: int, dtyp: str) -> Dict:
        return {
            'telescope_id': self.telescope.id,
            'ts': dt_utcnow_array(),
            'request': req,
            'fits_id': fits_id,
            'file_location': self.target_folder,
            'dtyp': dtyp,
            'mean_points_no_stats': mean_points_no_stats,
            'symlinks': self.symlinks,
            'header': header}

    async def rpc_request(self,
                          fits_id: str,
                          header: Dict,
                          req: str = 'fits_download',
                          mean_points_no_stats: int = 100,
                          dtyp: str = 'sideint16',
                          timeout: float = 120):

        inf = f'{self.id} {self.name} send rpc request {self.rpc_subject}'
        logger.debug(inf)
        await self.journal.debug(inf)
        dat, met = await request(subject=self.rpc_subject,
                                 data=self.rpc_data(fits_id=fits_id,
                                                    header=header,
                                                    req=req,
                                                    mean_points_no_stats=mean_points_no_stats,
                                                    dtyp=dtyp),
                                 timeout=timeout)

        inf = f'{self.id} {self.name} rpc response received.'
        logger.debug(inf)
        await self.journal.debug(inf)
        return dat

    def _get_folders_and_symlinks(self) -> None:
        self.symlinks = []
        if self.type == 'focusing':
            if self.seq_data.focus_folder:
                self.target_folder = self.seq_data.focus_folder
            else:
                try:
                    lst = os.listdir(self.fits_focus_folder)
                except FileNotFoundError:
                    lst = []
                lst_2 = [int(n) for n in lst if re.fullmatch(r'\d{6}', n)]
                if len(lst_2) == 0:
                    num_last = -1
                else:
                    num_last = max(lst_2)
                num = num_last + 1
                ff_name = f'{num:06d}'
                self.target_folder = os.path.join(self.fits_focus_folder, ff_name)
                self.seq_data.focus_folder = self.target_folder
                self.symlinks.append({'target': f'./{ff_name}',
                                      'symlink': os.path.join(self.fits_focus_folder, f'actual')})
            self.symlinks.append({'target': os.path.join(self.target_folder, f'{self.fits_file_name}.fits'),
                                  'symlink': os.path.join(self.fits_main_folder, 'last_shoot.fits')})
        elif self.type == 'snap':
            self.target_folder = self.fits_main_folder
            self.symlinks.append({'target': f'./{self.fits_file_name}.fits',
                                  'symlink': os.path.join(self.fits_main_folder, 'last_shoot.fits')})
        else:
            today_symlink_name = self._get_today_symlink_name()
            today_fits_folder_name = self._get_today_fits_folder_name()
            self.target_folder = os.path.join(self.fits_main_folder, f'{today_fits_folder_name}')
            self.symlinks.append({'target': f'./{today_fits_folder_name}',
                                  'symlink': os.path.join(self.fits_main_folder, f'actual')})
            self.symlinks.append({'target': f'./{today_fits_folder_name}',
                                  'symlink': os.path.join(self.fits_main_folder, today_symlink_name)})
            self.symlinks.append({'target': f'./{today_fits_folder_name}/{self.fits_file_name}.fits',
                                  'symlink': os.path.join(self.fits_main_folder, 'last_shoot.fits')})

    async def _wait_for_save_fits(self, sub: int, sub_time: float) -> bool:

        self._get_fits_file_name()
        self._get_folders_and_symlinks()

        gainmode = await self.value_proof_get(name='fitsh_cam_gain',
                                              awaitab=self.camera.aget_gain,
                                              expect_type=int)
        readoutmode = await self.value_proof_get(name='fitsh_cam_rm',
                                                 awaitab=self.camera.aget_readoutmode,
                                                 expect_type=int)
        filter = await self.value_proof_get(name='fitsh_filter',
                                            awaitab=self.filter_wheel.aget_position,
                                            expect_type=int)
        filters = await self.value_proof_get(name='fitsh_filters',
                                             awaitab=self.filter_wheel.aget_names,
                                             expect_type=dict)

        try:
            inv_f_map = {v: k for k, v in filters.items()}
            filter_str = inv_f_map[filter]
        except KeyError:
            filter_str = str(self.filter)

        if self.req_ra is None:
            req_ra = ''
        else:
            req_ra = self.req_ra

        if self.req_dec is None:
            req_dec = ''
        else:
            req_dec = self.req_dec

        # TODO This OCA should be taken from settings
        OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
        header = fits_header(
            obs_lat=OCA['latitude'],
            obs_lon=OCA['longitude'],
            obs_elev=OCA['elevation'],
            tel_id=str(self.telescope.id),
            utc_now=str(self.exp_time_start.isoformat(sep='T', timespec='auto')),
            jd=self.get_julian_date(self.exp_time_start),
            req_ra=req_ra,
            req_dec=req_dec,
            epoch=self.epoch,
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
            observer=str(self.observer),
            image_type=str(self.type),
            obs_type=self.obs_type,
            object=str(self.obj_name),
            n_loops=self.exp_no,
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

        try:
            dat = await self.rpc_request(fits_id=self.fits_file_name,
                                         header=header,
                                         dtyp=self.array_bits(rmmode=readoutmode))
        except (MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout):
            inf = f'{self.id} {self.name} nats rpc guider msg can not reach responder.'
            logger.error(inf)
            await self.journal.error(inf)
            self.info_callback['stream_1'](inf)
            return False
        if dat:
            try:
                if dat['response'] == 'fits_saved':
                    inf = f'{self.id} {self.name} exp:{sub}/{self.exp_no} done.'
                    logger.info(inf)
                    await self.journal.info(inf)
                    self.info_callback['stream_1'](inf)
                    self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                                   exp_done=True,
                                                                   exp_saved=True,
                                                                   n_exp=sub,
                                                                   mean=round(dat['param']['mean']),
                                                                   exp_time=sub_time,
                                                                   **self.info_dict))
                    return True
                else:
                    inf = f'{self.id} {self.name} wrong rpc response, no fits_saved.'
                    logger.error(inf)
                    await self.journal.error(inf)
                    self.info_callback['stream_1'](inf)
                    return False
            except KeyError:
                inf = f'{self.id} {self.name} wrong rpc response, KeyError.'
                logger.error(inf)
                await self.journal.error(inf)
                self.info_callback['stream_1'](inf)
                return False
        else:
            inf = f'{self.id} {self.name} wrong rpc response, dat is None.'
            logger.error(inf)
            await self.journal.error(inf)
            self.info_callback['stream_1'](inf)
            return False

    async def _wait_for_subexposure(self, sub_time: float) -> None:
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
                break
            await asyncio.sleep(0.1)

    async def get_array_autoexp(self, test_exp_time: float) -> List:
        await self.camera.aput_startexposure(test_exp_time, self.light)
        await self._wait_for_subexposure(test_exp_time)
        return await self.value_proof_get(name='autoexp_get_array',
                                         awaitab=self.camera.aget_imagearray,
                                         expect_type=list)

    async def _autoexposure_exec(self) -> Tuple[float, bool]:
        """
        TODO for filter, time, make test shot on sky with 1s exposure. If value is not what You expect wait
        some time and make test shot again until You don't get expected value of adu, then continue to make
        normal exposure with calculated length of exposure. On another sub, test shot calculation will be
        repeated, up to end.
        """
        inf = f'{self.id} auto skyflat procedure started.'
        logger.info(inf)
        await self.journal.info(inf)
        self.info_callback['stream_1'](inf)
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
        # TODO calculate according to location -
        longitude = -70.196389
        s = longitude / abs(longitude)
        h = (datetime.datetime.utcnow() + s * datetime.timedelta(minutes=abs(longitude) * 4)).hour
        if h > 12:
            evening = True
            ev_fact = evening_factor
        else:
            evening = False
            ev_fact = 1
        while True:
            inf = f'{self.id} {self.name} filter: {self.filter} starting test exposure.'
            logger.info(inf)
            await self.journal.info(inf)
            self.info_callback['stream_1'](inf)
            auto_exp_sub_no += 1

            await self.camera.aput_startexposure(test_exposure_time, self.light)
            await self._wait_for_subexposure(test_exposure_time)

            try:
                dat = await self.rpc_request(fits_id=f'{round((time.time())*10)}'[-7:],
                                             header={},
                                             req='stats_only')
            except (MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout):
                inf = f'{self.id} {self.name} nats rpc guider msg can not reach responder.'
                logger.error(inf)
                await self.journal.error(inf)
                self.info_callback['stream_1'](inf)
                return 0, True
            if dat:
                try:
                    if dat['response'] == 'stats_done':
                        mean = dat['param']['mean']
                    else:
                        inf = f'{self.id} {self.name} wrong rpc response, no stats_done.'
                        logger.error(inf)
                        await self.journal.error(inf)
                        self.info_callback['stream_1'](inf)
                        return 0, True
                except KeyError:
                    inf = f'{self.id} {self.name} wrong rpc response, key error.'
                    logger.error(inf)
                    await self.journal.error(inf)
                    self.info_callback['stream_1'](inf)
                    return 0, True
            else:
                inf = f'{self.id} {self.name} wrong rpc response, dat is None.'
                logger.error(inf)
                await self.journal.error(inf)
                self.info_callback['stream_1'](inf)
                return 0, True

            self.info_callback['exec_json'](self.exec_json(auto_exp_start=True,
                                                           auto_exp_finnished=True,
                                                           auto_exp_sub_no=auto_exp_sub_no,
                                                           auto_exp_time=test_exposure_time,
                                                           **self.info_dict))

            # Substract zero from mean and add to mean_list (plus some info)
            if mean > zero_level:
                mean = mean - zero_level
            else:
                mean = 1.0
            mean_list.append(mean)
            inf = (f'{self.id} Test frame filter: {self.filter} mean:{round(mean, 2)}'
                   f' range:[{round(test_min_max_adu[0]/test_min_max_time_exp[1], 2)}-'
                   f'{round(test_min_max_adu[1]/test_min_max_time_exp[0], 2)}]')
            logger.info(inf)
            await self.journal.info(inf)
            self.info_callback['stream_1'](inf)
            self.info_callback['exec_json'](self.exec_json(
                **self.info_dict,
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
                    inf = f"{self.id} autoflat filter: {self.filter} skipped - too dark."
                    logger.info(inf)
                    await self.journal.info(inf)
                    self.info_callback['stream_1'](inf)
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                    self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                    self.seq_data.skip = True
                    return 0, True
                # Morning
                elif not evening and mean_diff > 0 and mean_min_max[0] > test_min_max_adu[1]:
                    inf = f"{self.id} autoflat filter: {self.filter} skipped - too bright."
                    logger.info(inf)
                    await self.journal.info(inf)
                    self.info_callback['stream_1'](inf)
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                    self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                    self.seq_data.skip = True
                    return 0, True

            # Try to calculate exposure time, if fail next loop starts
            if test_min_max_adu[0] - mean_min_max[1] < 0 < test_min_max_adu[1] - mean_min_max[0]:
                if mean_min_max[0] < test_min_max_adu[0]:
                    exposure_time = (test_min_max_adu[0] / mean) * ev_fact
                    inf = (f"{self.id} {self.name} calc_exp_time:{round(exposure_time, 1)},"
                           f" expect_adu:{round(exposure_time * mean, 1)}")
                    logger.info(inf)
                    await self.journal.info(inf)
                    self.info_callback['stream_1'](inf)

                    return exposure_time, False
                else:
                    exposure_time = (mean_min_max[0] / mean) * ev_fact
                    inf = (f"{self.id} calc_exp_time:{round(exposure_time, 1)},"
                           f" expect_adu:{round(exposure_time * mean, 1)}")
                    logger.info(inf)
                    await self.journal.info(inf)
                    self.info_callback['stream_1'](inf)

                    return exposure_time, False
            await asyncio.sleep(test_time_interval)

    async def arun(self, step_id: str or None = None) -> int:

        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        if self.seq_data.skip:
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
            if self.sub_exp == self.exp_no:
                self.seq_data.skip = False
            return 0
        inf = f'{self.id} {self.name} started.'
        logger.debug(inf)
        await self.journal.debug(inf)

        exposure_time = self.seq_data.exp_time

        if self.auto_exposure:
            exposure_time, _exit = await self._autoexposure_exec()
            if _exit:
                return 0
        inf = f'{self.id} {self.name} exp: {self.sub_exp}/{self.exp_no} started.'
        logger.info(inf)
        await self.journal.info(inf)
        self.info_callback['stream_1'](inf)
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=False,
                                                       exp_saved=False,
                                                       n_exp=self.sub_exp,
                                                       **self.info_dict,
                                                       exp_time=float(exposure_time)))
        self.readout_time_start = time.time()
        self.exp_time_start = datetime.datetime.utcnow()
        await self.camera.aput_startexposure(float(exposure_time), self.light)
        await self._wait_for_subexposure(float(exposure_time))
        self.readout_time = time.time() - self.readout_time_start - float(exposure_time)
        inf = f'{self.id} {self.name} exp:{self.sub_exp}/{self.exp_no} saving.'
        logger.info(inf)
        await self.journal.info(inf)
        self.info_callback['stream_1'](f'{self.id} {self.name} exp:{self.sub_exp}/{self.exp_no} --> saving')
        self.info_callback['exec_json'](self.exec_json(exp_started=True,
                                                       exp_done=True,
                                                       exp_saved=False,
                                                       **self.info_dict,
                                                       readout_time=self.readout_time,
                                                       n_exp=self.sub_exp,
                                                       exp_time=float(exposure_time)))
        wff = await self._wait_for_save_fits(sub=self.sub_exp, sub_time=float(exposure_time))
        if not wff:
            return 2
        self.info_callback['stream_1'](f'{self.id} {self.name} done')
        self.info_callback['stream_5'](f'{self.id}')
        inf = f'{self.id} {self.name} done.'
        logger.debug(inf)
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(exp_time=float(exposure_time),
                                                       **self.info_dict))
        await asyncio.sleep(0.2)
        return 0
