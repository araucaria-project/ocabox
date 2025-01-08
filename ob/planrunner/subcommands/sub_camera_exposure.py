import asyncio
import logging
from typing import Callable, Dict, Any, Optional
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
from pyaraucaria.date import get_oca_jd
from pyaraucaria.airmass import airmass
from ob.planrunner.status import PlanStatusEnum


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(BaseSubCommand):

    FORCED_RM_MODE_SETTLE_TIME = 2 # seconds

    def __init__(
            self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable], seq_data: 'Seq', uobi: int,
            exp_type: str, filter_: str, light: bool, sub_exp: int, exp_no: int, auto_exposure: bool,
            epoch: str, observer: str, obj_name: str, req_ra: float or None = None, req_dec: float or None = None,
            test: int = 0, forced_read_mod: int or None = None, name: str = 'camera-exposure',
            param: Dict[str, Any] or None = None) -> None:

        self.seq_data = seq_data
        self.exp_type = exp_type
        self.filter_ = filter_
        self.light = light
        self.sub_exp = sub_exp
        self.exp_no = exp_no
        self.auto_exposure = auto_exposure
        self.epoch = epoch
        self.observer = observer
        self.obj_name = obj_name
        self.req_ra = req_ra
        self.req_dec = req_dec
        self.test = test
        self.forced_read_mod = forced_read_mod
        self.target_folder: str or None = None
        self.symlinks: List = []
        self.readout_time: float or None = None
        self.readout_time_start: float or None = None
        self.exp_time_start: str or None = None
        self.fits_file_name: str or None = None
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi, param=param)
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self.cover = self.telescope.get_covercalibrator()
        self.filter_wheel = self.telescope.get_filterwheel()
        self.focuser = self.telescope.get_focuser()
        self.rotator = self.telescope.get_rotator()

        self.info_dict = {
            'type': self.exp_type,
            'filter': filter_,
            'light': light,
            'sub_exp': sub_exp,
            'exp_no': exp_no,
            'auto_exposure': auto_exposure,
            'epoch': epoch,
            'observer': observer,
            'obj_name': obj_name,
            'req_ra': req_ra,
            'req_dec': req_dec
        }
        self.create_sub_command_string(**self.info_dict)

    @staticmethod
    def add_zero(numb: int):
        return f'{numb:02d}'

    async def gain_value(self, gain_mode: int) -> float or str:
        _gain = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera', 'gain_modes', str(gain_mode)
        ], source='nats')
        try:
            return _gain['gain']
        except (LookupError, TypeError):
            logger.info(f'No gain value in gain modes in general config')
            return ''

    @staticmethod
    async def airmass_value(alt: float) -> float or str:
        try:
            air = airmass(elevation=alt)
            if air is None:
                return ''
            else:
                return air
        except ValueError:
            return ''

    async def readout_noise_value(self, rmmode: int) -> float or str:
        _gain = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera', 'readout_modes', str(rmmode)
        ], source='nats')
        try:
            return _gain['ron']
        except (LookupError, TypeError):
            logger.info(f'No readout noise value in readout modes in general config')
            return ''

    async def pixel_scale(self) -> float or str:
        _cam = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera'
        ], source='nats')
        try:
            return _cam['pixel_scale']
        except (LookupError, TypeError):
            logger.info(f'No pixel scale value in camera in general config')
            return ''

    async def vertical_shift_speed(self) -> float or str:
        _cam = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera'
        ], source='nats')
        try:
            return _cam['vertical_shift_speed']
        except (LookupError, TypeError):
            logger.info(f'No vertical shift speed value in camera in general config')
            return ''

    async def zero_era(self) -> int or str:
        _era = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera', 'zero'
        ], source='nats')
        try:
            return _era['era']
        except (LookupError, TypeError):
            logger.info(f'No zero era value in camera in general config')
            return ''

    async def dark_era(self) -> int or str:
        _era = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera', 'dark'
        ], source='nats')
        try:
            return _era['era']
        except (LookupError, TypeError):
            logger.info(f'No dark era value in camera in general config')
            return ''

    async def sky_flats_era(self) -> int or str:
        _era = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera', 'sky_flats'
        ], source='nats')
        try:
            return _era['era']
        except (LookupError, TypeError):
            logger.info(f'No sky flats era value in camera in general config')
            return ''

    async def baseline_clamp(self) -> float or str:
        _cam = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera'
        ], source='nats')
        try:
            if _cam['baseline_clamp']:
                return 1
            else:
                return 0
        except (LookupError, TypeError):
            logger.info(f' No baseline clamp value in camera in general config')
            return ''

    async def sensor_port(self) -> float or str:
        _cam = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera'
        ], source='nats')
        try:
            return _cam['sensor_port']
        except (LookupError, TypeError):
            logger.info(f' No sensor port value in camera in general config')
            return ''

    async def sensor_compensation(self) -> float or str:
        _cam = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera'
        ], source='nats')
        try:
            if _cam['sensor_compensation']:
                return 1
            else:
                return 0
        except (LookupError, TypeError):
            logger.info(f' No sensor compensation value in camera in general config')
            return ''

    def array_bits(self, rmmode: int) -> str:
        rm = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'camera', 'readout_modes', str(rmmode)
        ], source='nats')
        try:
            bit = rm['bits']
        except (LookupError, TypeError):
            logger.error(f' No bit value in rm modes in general config')
            bit = 16
        if bit <= 16:
            return 'sideint16'
        else:
            return 'int32'

    @property
    def obs_type(self) -> str:
        if self.exp_type == 'snap':
            return f'test'
        elif self.exp_type == 'focusing':
            return f'focus'
        elif self.exp_type in ['flat', 'dark', 'zero']:
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
        return f"{math.floor(get_oca_jd(self.get_julian_date(str(datetime.datetime.utcnow())))):04.0f}"

    def _get_fits_file_name(self):
        if self.exp_type == 'snap':
            self.fits_file_name = f'snap'
        else:
            jd = self.get_julian_date(self.exp_time_start)
            jd_oca = f"{get_oca_jd(jd):010.5f}"
            self.fits_file_name = f'{self.telescope.id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}'

    @property
    def rpc_subject(self) -> str:
        r = self.param['cfg_gen'].get_value(
            seq=['site', 'global', 'nats', 'subjects', 'rpc', 'download'],
            source='nats'
        )
        return r

    def rpc_data(self, fits_id: str, header: Dict, req: str, mean_points_no_stats: int, dtyp: str) -> Dict:
        return {
            'telescope_id': self.telescope.id,
            'ts': dt_utcnow_array(),
            'request': req,
            'fits_id': fits_id,
            'file_location': self.target_folder,
            'dtyp': dtyp,
            'mean_points_no_stats': mean_points_no_stats,
            'symlinks': self.symlinks,
            'header': header
        }

    async def rpc_request(
            self, fits_id: str, header: Dict, req: str = 'fits_download', mean_points_no_stats: int = 400,
            dtyp: str = 'sideint16', timeout: float or None = None) -> Dict or None:

        inf = f'{self.id} {self.name} send rpc request {self.rpc_subject}'
        logger.info(inf)
        await self.journal.debug(inf)
        dat, met = await request(
            subject=self.rpc_subject,
            data=self.rpc_data(
                fits_id=fits_id, header=header, req=req, mean_points_no_stats=mean_points_no_stats, dtyp=dtyp
            ),
            timeout=timeout
        )

        inf = f'{self.id} {self.name} rpc response received.'
        logger.debug(inf)
        await self.journal.info(inf)
        logger.info(f'Data: {dat}')
        logger.info(f'Data: {met}')
        if 'error' in met:
            logger.error(f'Meta error: {met["error"]}')
        return dat

    def _get_folders_and_symlinks(self) -> None:
        self.symlinks = []
        if self.exp_type == 'focusing':
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
                self.symlinks.append({
                    'target': f'./{ff_name}',
                    'symlink': os.path.join(self.fits_focus_folder, f'actual')
                })
            self.symlinks.append({
                'target': os.path.join(self.target_folder, f'{self.fits_file_name}.fits'),
                'symlink': os.path.join(self.fits_main_folder, 'last_shoot.fits')
            })
        elif self.exp_type == 'snap':
            self.target_folder = self.fits_main_folder
            self.symlinks.append({
                'target': f'./{self.fits_file_name}.fits',
                'symlink': os.path.join(self.fits_main_folder, 'last_shoot.fits')
            })
        else:

            today_symlink_name = self._get_today_symlink_name()
            today_fits_folder_name = self._get_today_fits_folder_name()
            self.target_folder = os.path.join(
                self.fits_main_folder, self.fits_raw_folder_name, f'{today_fits_folder_name}'
            )
            self.symlinks.append({
                'target': f'./{self.fits_raw_folder_name}/{today_fits_folder_name}',
                'symlink': os.path.join(self.fits_main_folder, f'actual')
            })
            self.symlinks.append({
                'target': f'./{today_fits_folder_name}',
                'symlink': os.path.join(self.fits_main_folder, self.fits_raw_folder_name, today_symlink_name)
            })
            self.symlinks.append({
                'target': f'./{self.fits_raw_folder_name}/{today_fits_folder_name}/{self.fits_file_name}.fits',
                'symlink': os.path.join(self.fits_main_folder, 'last_shoot.fits')
            })

    async def _wait_for_save_fits(self, sub: int, sub_time: float) -> bool:
        logger.info('Wait for save fits ...')
        self._get_fits_file_name()
        self._get_folders_and_symlinks()

        gainmode = await self.value_proof_get(
            name='fitsh_cam_gain', awaitab=self.camera.aget_gain, expect_type=int
        )
        readoutmode = await self.value_proof_get(
            name='fitsh_cam_rm', awaitab=self.camera.aget_readoutmode, expect_type=int
        )
        _filter = await self.value_proof_get(
            name='fitsh_filter', awaitab=self.filter_wheel.aget_position, expect_type=int
        )
        filters = await self.get_filters_dict()
        try:
            inv_f_map = {v: k for k, v in filters.items()}
            filter_str = inv_f_map[_filter]
        except KeyError:
            filter_str = str(self.filter_)

        if self.req_ra is None:
            req_ra = ''
        else:
            req_ra = self.req_ra

        if self.req_dec is None:
            req_dec = ''
        else:
            req_dec = self.req_dec
        mount_type = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'mount', 'type'
        ], source='nats')
        if mount_type == 'eq':
            rot_pos = ''
            side_of_pier = await self.value_proof_get(
                name='mount_sideofpier', awaitab=self.mount.aget_sideofpier, expect_type=int
            )
        else:
            rot_pos = await self.value_proof_get(
                name='fitsh_rot_pos', awaitab=self.rotator.aget_position, expect_type=float, n_times=1
            )
            # if rot_pos is None:
            #     rot_pos = await self.value_proof_get(
            #         name='fitsh_rot_mechpos', awaitab=self.rotator.aget_mechanicalposition(),
            #         expect_type=float, n_times=1
            #     )
            if rot_pos is None:
                rot_pos = ''
            side_of_pier = ''
        instrument_name = str(await self.value_proof_get(
            name='fitsh_cam_sens_name', awaitab=self.camera.aget_sensorname, expect_type=str)
                              )
        if self.telescope.id == 'dev':
            instrument_name = 'simul'
        loc = self.param['cfg_gen'].get_value(seq=['site', 'global', 'geo_location'], source='nats')
        tel_alt = await self.value_proof_get(name='fitsh_tel_alt', awaitab=self.mount.aget_alt, expect_type=float)
        z_era = await self.zero_era()
        d_era = await self.dark_era()
        f_era = await self.sky_flats_era()
        header = fits_header(
            obs_lat=loc['lat'],
            obs_lon=loc['lon'],
            obs_elev=loc['elev'],
            tel_id=str(self.telescope.id),
            utc_now=str(self.exp_time_start.isoformat(sep='T', timespec='auto')),
            jd=self.get_julian_date(self.exp_time_start),
            req_ra=req_ra,
            req_dec=req_dec,
            epoch=self.epoch,
            tel_ra=await self.value_proof_get(name='fitsh_tel_ra', awaitab=self.mount.aget_ra, expect_type=float),
            tel_dec=await self.value_proof_get(name='fitsh_tel_dec', awaitab=self.mount.aget_dec, expect_type=float),
            tel_alt=tel_alt,
            tel_az=await self.value_proof_get(name='fitsh_tel_az', awaitab=self.mount.aget_az, expect_type=float),
            focus=await self.value_proof_get(
                name='fitsh_focus_pos', awaitab=self.focuser.aget_position, expect_type=int
            ),
            rotator_pos=rot_pos,
            observer=str(self.observer),
            image_type=str(self.exp_type),
            obs_type=self.obs_type,
            object=str(self.obj_name),
            n_loops=self.exp_no,
            loop=sub,
            filter=filter_str,
            exp_time=sub_time,
            instrume_name=instrument_name,
            ccd_temp=await self.value_proof_get(
                name='fitsh_cam_temp', awaitab=self.camera.aget_ccdtemperature, expect_type=float
            ),
            binx=await self.value_proof_get(
                name='fitsh_cam_binx', awaitab=self.camera.aget_binx, expect_type=int
            ),
            biny=await self.value_proof_get(
                name='fitsh_cam_biny', awaitab=self.camera.aget_biny, expect_type=int
            ),
            read_mod=readoutmode,
            gain_mod=gainmode,
            r_noise=await self.readout_noise_value(rmmode=readoutmode),
            gain=await self.gain_value(gain_mode=gainmode),
            scale=await self.pixel_scale(),
            pierside=side_of_pier,
            airmass=await self.airmass_value(alt=tel_alt),
            vertical_shift_speed=await self.vertical_shift_speed(),
            baseline_clamp=await self.baseline_clamp(),
            sensor_port=await self.sensor_port(),
            sensor_compensation=await self.sensor_compensation(),
            zero_era=z_era,
            dark_era=d_era,
            flat_era=f_era,
            test=self.test
        )
        try:
            dat = await self.rpc_request(
                fits_id=self.fits_file_name, header=header, dtyp=self.array_bits(rmmode=readoutmode), timeout=30
            )
        except (MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout):
            inf = f'{self.id} {self.name} nats rpc guider msg can not reach responder.'
            logger.error(inf)
            await self.journal.error(inf)
            self.info_callback['stream_1'](inf)
            return False
        if dat:
            try:
                if dat['response'] == 'fits_saved':
                    logger.info('Rpc response received.')
                    adu_mean = round(dat['param']['mean'])
                    logger.info(f'Adu mean {adu_mean}.')
                    if self.auto_exposure:
                        await self.seq_data.auto_flat.add_record(
                            ts_start=float(self.exp_time_start.timestamp()),
                            adu_mean=float(adu_mean),
                            exp=float(sub_time)
                        )
                    inf = f'{self.id} {self.name} exp:{sub}/{self.exp_no} done. Fits id: {self.fits_file_name}.'
                    logger.info(inf)
                    await self.journal.info(inf)
                    self.info_callback['stream_1'](inf)
                    self.info_callback['exec_json'](self.exec_json(
                        exp_started=True, exp_done=True, exp_saved=True, n_exp=sub, mean=adu_mean,
                        exp_time=sub_time, **self.info_dict)
                    )
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

    async def wait_for_subexposure(self, sub_time: float) -> None:
        logger.info('Waiting for camera image ready ...')
        if sub_time >= 4.0:
            sub_t = sub_time
        else:
            sub_t = 4.0
        await asyncio.sleep(float(sub_t))
        while True:
            subexposure_done = await self.value_proof_get(
                name='wait_subexp', awaitab=self.camera.aget_imageready, expect_type=bool
            )
            if subexposure_done is True:
                logger.info('Wait for camera done.')
                break
            await asyncio.sleep(0.5)

    async def forced_read_mod_change(self) -> int:

        inf = f'Readout mode forced change to {self.forced_read_mod} started.'
        logger.info(inf)
        await self.journal.info(inf)
        _current_rm_mode = await self.value_proof_get(
            name='forced_cam_read_mod', awaitab=self.camera.aget_readoutmode, expect_type=int
        )
        if _current_rm_mode is not None and isinstance(_current_rm_mode, int):
            if _current_rm_mode == self.forced_read_mod:
                inf = (f'{self.id} {self.name} forced readout mode {self.forced_read_mod}'
                       f' is equal to set {_current_rm_mode}, no change.')
                logger.info(inf)
                await self.journal.info(inf)
                self.info_callback['stream_1'](inf)
                return 0
            elif _current_rm_mode != self.forced_read_mod:
                exe = await self.proof_put(
                    awaitab=self.camera.aput_readoutmode, romode=self.forced_read_mod
                )
                if not exe:
                    inf = f'{self.id} {self.name} can not set readout mode {self.forced_read_mod}, program quiting.'
                    logger.error(inf)
                    await self.journal.error(inf)
                    self.info_callback['stream_1'](inf)
                    return 2
                await asyncio.sleep(self.FORCED_RM_MODE_SETTLE_TIME)
                inf = f'{self.id} {self.name} readout mode changed from {_current_rm_mode} to {self.forced_read_mod}.'
                logger.info(inf)
                await self.journal.info(inf)
                self.info_callback['stream_1'](inf)
                return 0
        else:
            inf = f'{self.id} {self.name} can not read current readout mode or is not [int], program quiting.'
            logger.error(inf)
            await self.journal.error(inf)
            self.info_callback['stream_1'](inf)
            return 2

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
        logger.info(inf)
        await self.journal.debug(inf)
        if self.forced_read_mod is not None:
            _exit = await self.forced_read_mod_change()
            if _exit == 2:
                return 2

        exposure_time = self.seq_data.exp_time

        if self.auto_exposure:
            self.seq_data.auto_flat.set_camera_exposure_parent(camera_exposure=self)
            exposure_time, _exit = await self.seq_data.auto_flat.exec()
            if _exit == 1:
                return 0
            elif _exit == 2:
                return 2
        inf = f'{self.id} {self.name} exp: {self.sub_exp}/{self.exp_no} started.'
        logger.info(inf)
        await self.journal.info(inf)
        self.info_callback['stream_1'](inf)
        self.info_callback['exec_json'](self.exec_json(
            exp_started=True, exp_done=False, exp_saved=False, n_exp=self.sub_exp,
            **self.info_dict, exp_time=float(exposure_time))
        )
        self.readout_time_start = time.time()
        self.exp_time_start = datetime.datetime.utcnow()
        exe = await self.proof_put(
            awaitab=self.camera.aput_startexposure, duration=float(exposure_time), light=self.light
        )
        if not exe:
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            inf = f'Can not execute startexposure, program stopping'
            logger.error(inf)
            await self.journal.error(inf)
            return 2
        await self.wait_for_subexposure(float(exposure_time))
        self.readout_time = time.time() - self.readout_time_start - float(exposure_time)
        inf = f'{self.id} {self.name} exp:{self.sub_exp}/{self.exp_no} saving.'
        logger.info(inf)
        await self.journal.info(inf)
        self.info_callback['stream_1'](f'{self.id} {self.name} exp:{self.sub_exp}/{self.exp_no} --> saving')
        self.info_callback['exec_json'](self.exec_json(
            exp_started=True, exp_done=True, exp_saved=False, **self.info_dict,
            readout_time=self.readout_time, n_exp=self.sub_exp, exp_time=float(exposure_time)
        ))
        wff = await self._wait_for_save_fits(sub=self.sub_exp, sub_time=float(exposure_time))
        if not wff:
            return 2
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(exp_time=float(exposure_time), **self.info_dict))
        self.info_callback['stream_1'](f'{self.id} {self.name} done')
        self.info_callback['stream_5'](f'{self.id}')
        inf = f'{self.id} {self.name} done.'
        logger.info(inf)
        self.done = True
        await asyncio.sleep(0.2)
        return 0
