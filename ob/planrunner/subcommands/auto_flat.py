import asyncio
import time
from asyncio import CancelledError

from scipy.optimize import curve_fit, OptimizeWarning
import numpy as np
from scipy.stats import linregress
from typing import Dict, List, Tuple, Any, Optional
import logging
import datetime

from serverish.base import MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout

from ob.planrunner.status import PlanStatusEnum

logger = logging.getLogger(__name__.rsplit('.')[-1])


class AutoFlatNoTest:

    def __init__(self) -> None:
        self.ce = None
        self.test_exposure_time: float = 1.0
        self.test_time_interval: float = 3.0
        self.range_min_max_adu: List = [20000, 25000]
        self.range_min_max_time_exp: List = [2, 30]
        self.zero_level: float = 300.0
        self.evening: bool = False
        self.ts_start: List[float] = []
        self.exposure: List[float] = []
        self.saturation: List[float] = []
        self.auto_exp_sub_no = 0

    def set_camera_exposure_parent(self, camera_exposure: Any) -> None:
        self.ce = camera_exposure

    async def _load_params(self):
        sky_flat_conf = self.ce.param['cfg_gen'].get_value(seq=[
            'telescopes', self.ce.telescope.id, 'observatory', 'components', 'camera', 'sky_flats'
        ], source='nats')
        try:
            self.test_exposure_time = sky_flat_conf['test_exp_time']
        except (LookupError, TypeError):
            logger.warning(f'No test_exp_time in general config.')
            pass
        try:
            self.test_time_interval = sky_flat_conf['test_exp_interval']
        except (LookupError, TypeError):
            logger.warning(f'No test_exp_interval in general config.')
            pass
        try:
            self.test_min_max_adu = sky_flat_conf['test_adu_range']
        except (LookupError, TypeError):
            logger.warning(f'No test_adu_range in general config.')
            pass
        try:
            self.test_min_max_time_exp = sky_flat_conf['exposure_time_range']
        except (LookupError, TypeError):
            logger.warning(f'No exposure_time_range in general config.')
            pass
        try:
            self.zero_level = sky_flat_conf['bias_level']
        except (LookupError, TypeError):
            logger.warning(f'No bias_level in general config.')
            pass

    async def _set_evening(self):
        loc = self.ce.param['cfg_gen'].get_value(seq=['site', 'global', 'geo_location'], source='nats')
        longitude = loc['lon']
        s = longitude / abs(longitude)
        h = (datetime.datetime.utcnow() + s * datetime.timedelta(minutes=abs(longitude) * 4)).hour
        if h > 12:
            self.evening = True
        else:
            self.evening = False
        logger.info(f'Evening set {self.evening}')

    async def add_record(self,ts_start: float, saturation: float, exp: float) -> None:
        self.ts_start.append(ts_start)
        self.saturation.append(saturation)
        self.exposure.append(exp)

    @staticmethod
    def _exp_func(x, a, b, c):
        return (a * (b ** x)) + c

    @staticmethod
    async def _curve_fit(x, y) -> np.ndarray or Tuple[None, None, None]:
        try:
            params = curve_fit(AutoFlatNoTest._exp_func, np.array(x), np.array(y))
            return params[0]
        except RuntimeError:
            logger.warning(f'Can not fit curve')
            return None, None, None

    @staticmethod
    async def _linear_saturation_predict(ts_mid_shift: np.ndarray, sat_sec: np.ndarray, ts_now: float) -> float:
        slope, intercept, r_value, p_value, std_err = linregress(ts_mid_shift, sat_sec)
        _saturation_predict = slope * ts_now + intercept
        return _saturation_predict

    async def _calculate_exposure_time(self, test_time: float = None) -> Tuple[float, float] or Tuple[None, None]:
        inf = f'Start calc. exp. time'
        logger.info(inf)
        await self.ce.journal.info(inf)
        self.ce.info_callback['stream_1'](inf)
        _sat_sec = ((np.array(self.saturation) - self.zero_level) / np.array(self.exposure)) + self.zero_level
        _ts_mid = np.array(self.ts_start) + (np.array(self.exposure) / 2)
        _ts_mid_min = _ts_mid.min()
        _ts_mid_shift = _ts_mid - _ts_mid_min
        if not test_time:
            _ts_now = time.time() - _ts_mid_min
        else:
            _ts_now = test_time - _ts_mid_min

        if len(self.saturation) == 1:
            _saturation_predict = self.saturation[0]

        elif len(self.saturation) == 2:
            _saturation_predict = await self._linear_saturation_predict(
                ts_mid_shift=_ts_mid_shift, sat_sec=_sat_sec, ts_now=_ts_now
            )

        elif len(self.saturation) > 2:
            a, b, c = await self._curve_fit(x=_ts_mid_shift, y=_sat_sec)
            if a is None or b is None or c is None:
                _saturation_predict = await self._linear_saturation_predict(
                    ts_mid_shift=_ts_mid_shift, sat_sec=_sat_sec, ts_now=_ts_now
                )
            else:
                _saturation_predict = self._exp_func(_ts_now, a, b, c)

        else:
            inf = f'No data to calc. time'
            logger.info(inf)
            await self.ce.journal.info(inf)
            self.ce.info_callback['stream_1'](inf)
            return None, None

        _new_exposure_min = self.range_min_max_adu[0] / _saturation_predict
        _new_exposure_max = self.range_min_max_adu[1] / _saturation_predict
        inf = f'Calc. exp. time done'
        logger.info(inf)
        await self.ce.journal.info(inf)
        self.ce.info_callback['stream_1'](inf)
        return _new_exposure_min, _new_exposure_max

    async def _evaluate_exposure_time(
            self, exposure_min: float, exposure_max: float) -> Tuple[float, float] or Tuple[None, None]:
        inf = f'Start valuate exp. time.'
        logger.info(inf)
        await self.ce.journal.info(inf)
        self.ce.info_callback['stream_1'](inf)
        if self.range_min_max_time_exp[1] >= exposure_min >= self.range_min_max_time_exp[0]:
            inf = f"{self.ce.id} {self.ce.name} calc_exp_time:{round(exposure_min, 1)}"
            logger.info(inf)
            await self.ce.journal.info(inf)
            self.ce.info_callback['stream_1'](inf)
            return exposure_min, 0
        elif exposure_min < self.range_min_max_time_exp[0] and exposure_max < self.range_min_max_time_exp[0]:
            if not self.evening:
                inf = f"{self.ce.id} auto skyflat filter: {self.ce.filter_} skipped - too bright."
                logger.info(inf)
                await self.ce.journal.info(inf)
                self.ce.info_callback['stream_1'](inf)
                self.ce.skipped = True
                await self.ce.param['plan_status'].upd_status(id=self.ce.id, value=PlanStatusEnum.skipped)
                self.ce.info_callback['exec_json'](self.ce.exec_json(**self.ce.info_dict))
                self.ce.seq_data.skip = True
                return 0, 1
            else:
                return None, None
        elif exposure_max > self.range_min_max_time_exp[1] and exposure_min > self.range_min_max_time_exp[1]:
            if self.evening:
                inf = f"{self.ce.id} auto skyflat filter: {self.ce.filter_} skipped - too dark."
                logger.info(inf)
                await self.ce.journal.info(inf)
                self.ce.info_callback['stream_1'](inf)
                self.ce.skipped = True
                await self.ce.param['plan_status'].upd_status(id=self.ce.id, value=PlanStatusEnum.skipped)
                self.ce.info_callback['exec_json'](self.ce.exec_json(**self.ce.info_dict))
                self.ce.seq_data.skip = True
                return 0, 1
            else:
                return None, None
        elif exposure_min < self.range_min_max_time_exp[0] and exposure_max < self.range_min_max_time_exp[1]:
            inf = f"{self.ce.id} {self.ce.name} calc_exp_time:{round(self.range_min_max_time_exp[0], 1)}"
            logger.info(inf)
            await self.ce.journal.info(inf)
            self.ce.info_callback['stream_1'](inf)
            return self.range_min_max_time_exp[0], 0
        else:
            return None, None

    async def _run_test_exposure(self) -> bool:

        inf = f'{self.ce.id} {self.ce.name} filter: {self.ce.filter_} starting test exposure.'
        logger.info(inf)
        await self.ce.journal.info(inf)
        self.ce.info_callback['stream_1'](inf)

        self.auto_exp_sub_no += 1

        _ts_start = time.time()
        exe = await self.ce.proof_put(
            awaitab=self.ce.camera.aput_startexposure, duration=self.test_exposure_time, light=self.ce.light
        )

        if not exe:
            self.ce.skipped = True
            await self.ce.param['plan_status'].upd_status(id=self.ce.id, value=PlanStatusEnum.error)
            inf = f'Can not execute start_exposure, program stopping'
            logger.error(inf)
            await self.ce.journal.error(inf)
            return False
        await self.ce.wait_for_subexposure(self.test_exposure_time)
        try:
            dat = await self.ce.rpc_request(
                fits_id=f'{round((time.time()) * 10)}'[-7:],
                header={},
                req='stats_only',
                timeout=30
            )
        except (MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout):
            inf = f'{self.ce.id} {self.ce.name} nats rpc msg can not reach responder.'
            logger.error(inf)
            await self.ce.journal.error(inf)
            self.ce.info_callback['stream_1'](inf)
            return False
        if dat:
            try:
                if dat['response'] == 'stats_done':
                    await self.add_record(
                        ts_start=_ts_start, saturation=dat['param']['mean'], exp=self.test_exposure_time
                    )
                else:
                    inf = f'{self.ce.id} {self.ce.name} wrong rpc response, no stats_done.'
                    logger.error(inf)
                    await self.ce.journal.error(inf)
                    self.ce.info_callback['stream_1'](inf)
                    return False
            except KeyError:
                inf = f'{self.ce.id} {self.ce.name} wrong rpc response, key error.'
                logger.error(inf)
                await self.ce.journal.error(inf)
                self.ce.info_callback['stream_1'](inf)
                return False
        else:
            inf = f'{self.ce.id} {self.ce.name} wrong rpc response, dat is None.'
            logger.error(inf)
            await self.ce.journal.error(inf)
            self.ce.info_callback['stream_1'](inf)
            return False

        self.ce.info_callback['exec_json'](self.ce.exec_json(
            auto_exp_start=True, auto_exp_finnished=True, auto_exp_sub_no=self.auto_exp_sub_no,
            auto_exp_time=self.test_exposure_time, **self.ce.info_dict)
        )
        return True

    async def _exec(self) -> Tuple[float, int]:

        if self.ce is None:
            logger.error('Parent camera_exposure not set')
            raise RuntimeError

        inf = f'{self.ce.id} auto skyflat procedure started.'
        logger.info(inf)
        await self.ce.journal.info(inf)
        self.ce.info_callback['stream_1'](inf)

        await self._set_evening()

        while True:
            _new_exposure_min, _new_exposure_max = await self._calculate_exposure_time()
            _exp_time, _skip = await self._evaluate_exposure_time(
                exposure_min=_new_exposure_min, exposure_max=_new_exposure_max
            )
            if _exp_time is not None and _skip is not None:
                return _exp_time, _skip
            ok = await self._run_test_exposure()
            if not ok:
                return 0, 2
            await asyncio.sleep(self.test_time_interval)

    async def exec(self) -> Tuple[float, int]:
        _exp_time, _skip = await self._exec()
        return _exp_time, _skip


class AutoFlat:

    TEST_BIN_X = 2
    TEST_BIN_Y = 2
    TEST_RM_MODE = 1
    RM_MOD_FACTOR = 1

    def __init__(self) -> None:
        self.ce: Any = None
        self.test_exposure_time: float = 1.0
        self.test_time_interval: float = 1.0
        self.test_min_max_adu: List = [20000, 25000]
        # self.test_min_max_time_exp: List = [10, 60]
        self.test_min_max_time_exp: List = [2, 30]
        self.zero_level: float = 290.0
        self.evening_factor: float = 1.11
        self.mean_list: List = []
        self.mean_diff: Optional[float] = None
        self.auto_exp_sub_no: int = 0
        self.evening: bool = False
        self.saturation_factor: float = 1
        self.mean_min_max: List = []
        self.last_mean: float = 0
        self.initial_rm_mode: Optional[int] = None
        self.initial_bin_x: Optional[int] = None
        self.initial_bin_y: Optional[int] = None
        self.cameraxsize: Optional[int] = None
        self.cameraysize: Optional[int] = None

    def set_camera_exposure_parent(self, camera_exposure: Any) -> None:
        self.ce = camera_exposure

    async def _load_params(self):
        sky_flat_conf = self.ce.param['cfg_gen'].get_value(seq=[
            'telescopes', self.ce.telescope.id, 'observatory', 'components', 'camera', 'sky_flats'
        ], source='nats')
        try:
            self.test_exposure_time = sky_flat_conf['test_exp_time']
        except (LookupError, TypeError):
            logger.warning(f'No test_exp_time in general config.')
            pass
        try:
            self.test_time_interval = sky_flat_conf['test_exp_interval']
        except (LookupError, TypeError):
            logger.warning(f'No test_exp_interval in general config.')
            pass
        try:
            self.test_min_max_adu = sky_flat_conf['test_adu_range']
        except (LookupError, TypeError):
            logger.warning(f'No test_adu_range in general config.')
            pass
        try:
            self.test_min_max_time_exp = sky_flat_conf['exposure_time_range']
        except (LookupError, TypeError):
            logger.warning(f'No exposure_time_range in general config.')
            pass
        try:
            self.zero_level = sky_flat_conf['bias_level']
        except (LookupError, TypeError):
            logger.warning(f'No bias_level in general config.')
            pass
        try:
            self.evening_factor = sky_flat_conf['evening_factor']
        except (LookupError, TypeError):
            logger.warning(f'No evening_factor in general config.')
            pass

    async def _set_saturation_factor_and_evening(self):
        loc = self.ce.param['cfg_gen'].get_value(seq=['site', 'global', 'geo_location'], source='nats')
        longitude = loc['lon']
        s = longitude / abs(longitude)
        h = (datetime.datetime.utcnow() + s * datetime.timedelta(minutes=abs(longitude) * 4)).hour
        if h > 12:
            self.evening = True
            self.saturation_factor = self.evening_factor
        else:
            self.evening = False
            self.saturation_factor = 1

    async def get_last_mean(self) -> Tuple[float, int] or Tuple[None, None]:

        exe = await self.ce.proof_put(
            awaitab=self.ce.camera.aput_startexposure, duration=self.test_exposure_time, light=self.ce.light
        )

        if not exe:
            self.ce.skipped = True
            await self.ce.param['plan_status'].upd_status(id=self.ce.id, value=PlanStatusEnum.error)
            inf = f'Can not execute start_exposure, program stopping'
            logger.error(inf)
            await self.ce.journal.error(inf)
            return 0, 2
        await self.ce.wait_for_subexposure(self.test_exposure_time)
        try:
            dat = await self.ce.rpc_request(
                fits_id=f'{round((time.time()) * 10)}'[-7:],
                header={},
                req='stats_only',
                timeout=30
            )
        except (MessengerRequestNoResponders, MessengerRequestNoResponse, MessengerRequestTimeout):
            inf = f'{self.ce.id} {self.ce.name} nats rpc msg can not reach responder.'
            logger.error(inf)
            await self.ce.journal.error(inf)
            self.ce.info_callback['stream_1'](inf)
            return 0, 1
        if dat:
            try:
                if dat['response'] == 'stats_done':
                    self.last_mean = dat['param']['mean']
                else:
                    inf = f'{self.ce.id} {self.ce.name} wrong rpc response, no stats_done.'
                    logger.error(inf)
                    await self.ce.journal.error(inf)
                    self.ce.info_callback['stream_1'](inf)
                    return 0, 1
            except KeyError:
                inf = f'{self.ce.id} {self.ce.name} wrong rpc response, key error.'
                logger.error(inf)
                await self.ce.journal.error(inf)
                self.ce.info_callback['stream_1'](inf)
                return 0, 1
        else:
            inf = f'{self.ce.id} {self.ce.name} wrong rpc response, dat is None.'
            logger.error(inf)
            await self.ce.journal.error(inf)
            self.ce.info_callback['stream_1'](inf)
            return 0, 1

        self.ce.info_callback['exec_json'](self.ce.exec_json(
            auto_exp_start=True, auto_exp_finnished=True, auto_exp_sub_no=self.auto_exp_sub_no,
            auto_exp_time=self.test_exposure_time, **self.ce.info_dict)
        )
        if self.last_mean > self.zero_level:
            # included binning values
            self.last_mean = (self.last_mean - self.zero_level) \
                             * self.RM_MOD_FACTOR / (self.TEST_BIN_X * self.TEST_BIN_Y)
            # self.last_mean = self.last_mean  - self.zero_level
        else:
            self.last_mean = 1.0
        return None, None

    async def calc_mean_diff(self) -> None:
        if len(self.mean_list) > 1:
            self.mean_diff = self.mean_list[-1] - self.mean_list[-2]
        else:
            self.mean_diff = None

    async def calc_mean_min_max(self) -> None:
        # Calculate mean range times minimal and maximal accepted exposure time
        self.mean_min_max = (
            self.test_min_max_time_exp[0] * self.last_mean,
            self.test_min_max_time_exp[1] * self.last_mean
        )

    async def check_if_skipp_this_filter(self) -> Tuple[float, int] or Tuple[None, None]:
        # Check if we should skipp this filter for good
        if self.mean_diff is not None:
            # Evening
            if self.evening and self.mean_diff < 0 and self.mean_min_max[1] < self.test_min_max_adu[0]:
                inf = f"{self.ce.id} autoflat filter: {self.ce.filter_} skipped - too dark."
                logger.info(inf)
                await self.ce.journal.info(inf)
                self.ce.info_callback['stream_1'](inf)
                self.ce.skipped = True
                await self.ce.param['plan_status'].upd_status(id=self.ce.id, value=PlanStatusEnum.skipped)
                self.ce.info_callback['exec_json'](self.ce.exec_json(**self.ce.info_dict))
                self.ce.seq_data.skip = True
                return 0, 1
            # Morning
            elif not self.evening and self.mean_diff > 0 and self.mean_min_max[0] > self.test_min_max_adu[1]:
                inf = f"{self.ce.id} autoflat filter: {self.ce.filter_} skipped - too bright."
                logger.info(inf)
                await self.ce.journal.info(inf)
                self.ce.info_callback['stream_1'](inf)
                self.ce.skipped = True
                await self.ce.param['plan_status'].upd_status(id=self.ce.id, value=PlanStatusEnum.skipped)
                self.ce.info_callback['exec_json'](self.ce.exec_json(**self.ce.info_dict))
                self.ce.seq_data.skip = True
                return 0, 1
            else:
                return None, None
        return None, None

    async def calculate_exposure_time(self) -> Tuple[float, int] or Tuple[None, None]:
        # Try to calculate exposure time, if fail next loop starts
        if self.test_min_max_adu[0] - self.mean_min_max[1] < 0 < self.test_min_max_adu[1] - self.mean_min_max[0]:
            if self.mean_min_max[0] < self.test_min_max_adu[0]:
                exposure_time = (self.test_min_max_adu[0] / self.last_mean) * self.saturation_factor
                inf = (f"{self.ce.id} {self.ce.name} calc_exp_time:{round(exposure_time, 1)},"
                       f" expect_adu:{round(exposure_time * self.last_mean, 1)}")
                logger.info(inf)
                await self.ce.journal.info(inf)
                self.ce.info_callback['stream_1'](inf)

                return exposure_time, 0
            else:
                exposure_time = (self.mean_min_max[0] / self.last_mean) * self.saturation_factor
                inf = (f"{self.ce.id} calc_exp_time:{round(exposure_time, 1)},"
                       f" expect_adu:{round(exposure_time * self.last_mean, 1)}")
                logger.info(inf)
                await self.ce.journal.info(inf)
                self.ce.info_callback['stream_1'](inf)

                return exposure_time, 0
        return None, None

    async def _auto_exposure_exec(self) -> Tuple[float, int]:
        """
        For filter, time, make test shot on sky with 1s exposure. If value is not what You expect wait
        some time and make test shot again until You don't get expected value of adu, then continue to make
        normal exposure with calculated length of exposure. On another sub, test shot calculation will be
        repeated, up to end.
        """
        if self.ce is None:
            logger.error('Parent camera_expousure not set')
            raise RuntimeError

        inf = f'{self.ce.id} auto skyflat procedure started.'
        logger.info(inf)
        await self.ce.journal.info(inf)
        self.ce.info_callback['stream_1'](inf)

        await self._set_saturation_factor_and_evening()

        # Starting test exposure loop
        while True:

            inf = f'{self.ce.id} {self.ce.name} filter: {self.ce.filter_} starting test exposure.'
            logger.info(inf)
            await self.ce.journal.info(inf)
            self.ce.info_callback['stream_1'](inf)

            self.auto_exp_sub_no += 1

            _exp_time, _skip = await self.get_last_mean()
            if _exp_time is not None and _skip is not None:
                return _exp_time, _skip

            self.mean_list.append(self.last_mean)

            inf = (f'{self.ce.id} Test frame filter: {self.ce.filter_} mean:{round(self.last_mean, 2)}'
                   f' range:[{round(self.test_min_max_adu[0]/self.test_min_max_time_exp[1], 2)}-'
                   f'{round(self.test_min_max_adu[1]/self.test_min_max_time_exp[0], 2)}]')
            logger.info(inf)
            await self.ce.journal.info(inf)
            self.ce.info_callback['stream_1'](inf)

            self.ce.info_callback['exec_json'](self.ce.exec_json(
                **self.ce.info_dict,
                test_exp_mean=self.last_mean,
                expected_mean_min=round(self.test_min_max_adu[0]/self.test_min_max_time_exp[1]),
                expected_mean_max=round(self.test_min_max_adu[1]/self.test_min_max_time_exp[0]))
            )

            await self.calc_mean_diff()

            await self.calc_mean_min_max()

            _exp_time, _skip = await self.check_if_skipp_this_filter()
            if _exp_time is not None and _skip is not None:
                return _exp_time, _skip

            _exp_time, _skip = await self.calculate_exposure_time()
            if _exp_time is not None and _skip is not None:
                return _exp_time, _skip

            await asyncio.sleep(self.test_time_interval)

    async def set_cameraxsize(self):
        self.cameraxsize = await self.ce.value_proof_get(
            name='aget_cameraxsize', awaitab=self.ce.camera.aget_cameraxsize, expect_type=int
        )

    async def set_cameraysize(self):
        self.cameraysize = await self.ce.value_proof_get(
            name='aget_cameraysize', awaitab=self.ce.camera.aget_cameraysize, expect_type=int
        )

    async def set_initial_rm_mode(self):
        self.initial_rm_mode = await self.ce.value_proof_get(
            name='aget_readoutmode', awaitab=self.ce.camera.aget_readoutmode, expect_type=int
        )

    async def set_initial_bin_x(self):
        self.initial_bin_x = await self.ce.value_proof_get(
            name='aget_binx', awaitab=self.ce.camera.aget_binx, expect_type=int
        )

    async def set_initial_bin_y(self):
        self.initial_bin_y = await self.ce.value_proof_get(
            name='aget_biny', awaitab=self.ce.camera.aget_biny, expect_type=int
        )

    async def _wait_for_cam_params(
            self, readoutmode: int, bin_x: int, bin_y: int, numx: int, numy: int,
            timeout: float = 5.0) -> bool:
        _start_time = time.time()
        while True:
            c_par = await asyncio.gather(*[

                self.ce.value_proof_get(
                    name='aget_readoutmode', awaitab=self.ce.camera.aget_readoutmode, expect_type=int
                ),
                self.ce.value_proof_get(
                    name='aget_binx', awaitab=self.ce.camera.aget_binx, expect_type=int
                ),
                self.ce.value_proof_get(
                    name='aget_biny', awaitab=self.ce.camera.aget_biny, expect_type=int
                ),
                self.ce.value_proof_get(
                    name='aget_numx', awaitab=self.ce.camera.aget_numx, expect_type=int
                ),
                self.ce.value_proof_get(
                    name='aget_numy', awaitab=self.ce.camera.aget_numy, expect_type=int
                )
            ])
            if c_par[0] == readoutmode and c_par[1] == bin_x and c_par[2] == bin_y and \
                    c_par[3] == numx and c_par[4] == numy:
                return True
            if time.time() > _start_time + timeout:
                logger.error('Wait_for_cam_params timeout')
                break
            await asyncio.sleep(0)
        return False

    async def exec_no_rm_bin(self) -> Tuple[float, int]:
        _exp_time, _skip = await self._auto_exposure_exec()
        return _exp_time, _skip

    async def exec_rm_bin(self) -> Tuple[float, int]:

        await asyncio.gather(*[
            self.set_cameraxsize(),
            self.set_cameraysize(),
            self.set_initial_rm_mode(),
            self.set_initial_bin_x(),
            self.set_initial_bin_y(),
        ])

        inf = (f'x: {self.cameraxsize} y: {self.cameraysize} rm: {self.initial_rm_mode}'
               f' binx: {self.initial_bin_x} biny: {self.initial_bin_y}')
        logger.info(inf)
        await self.ce.journal.info(inf)

        try:
            await asyncio.gather(*[
                self.ce.proof_put(awaitab=self.ce.camera.aput_readoutmode, romode=self.TEST_RM_MODE),
                self.ce.proof_put(awaitab=self.ce.camera.aput_binx, binx=self.TEST_BIN_X),
                self.ce.proof_put(awaitab=self.ce.camera.aput_biny, biny=self.TEST_BIN_Y),
                self.ce.proof_put(awaitab=self.ce.camera.aput_numx, numx=int(self.cameraxsize / self.TEST_BIN_X)),
                self.ce.proof_put(awaitab=self.ce.camera.aput_numy, numy=int(self.cameraysize / self.TEST_BIN_Y))
            ])
            ok = await self._wait_for_cam_params(
                readoutmode=self.TEST_RM_MODE,
                bin_x=self.TEST_BIN_X,
                bin_y=self.TEST_BIN_Y,
                numx=int(self.cameraxsize / self.TEST_BIN_X),
                numy=int(self.cameraysize / self.TEST_BIN_Y)
            )
            if not ok:
                # TODO Logging errors here
                return 0, 2
            await asyncio.sleep(1)
            _exp_time, _skip = await self._auto_exposure_exec()
            return _exp_time, _skip
        except CancelledError:
            pass
        finally:
            inf = 'Setting rm mode and binning back to initial values'
            logger.info(inf)
            await self.ce.journal.info(inf)
            await asyncio.gather(*[
                self.ce.proof_put(awaitab=self.ce.camera.aput_readoutmode, romode=self.initial_rm_mode),
                self.ce.proof_put(awaitab=self.ce.camera.aput_binx, binx=self.initial_bin_x),
                self.ce.proof_put(awaitab=self.ce.camera.aput_biny, biny=self.initial_bin_y),
                self.ce.proof_put(awaitab=self.ce.camera.aput_numx, numx=self.cameraxsize),
                self.ce.proof_put(awaitab=self.ce.camera.aput_numy, numy=self.cameraysize)
            ])

            ok = await self._wait_for_cam_params(
                readoutmode=self.initial_rm_mode,
                bin_x=self.initial_bin_x,
                bin_y=self.initial_bin_y,
                numx=self.cameraxsize,
                numy=self.cameraysize
            )
            if not ok:
                # TODO Logging errors here
                return 0, 2

            await asyncio.sleep(1)

    async def exec(self, rm_bin_option: bool = True) -> Tuple[float, int]:
        if rm_bin_option:
            _exp_time, _skip = await self.exec_rm_bin()
        else:
            _exp_time, _skip = await self.exec_no_rm_bin()
        return _exp_time, _skip