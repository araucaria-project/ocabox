import datetime
import logging
from typing import List, Any, Dict, Callable
from ob.planrunner.base_sequence import BaseSequence
from ob.planrunner.sequence import Sequence
from ob.planrunner.cycle_time_calc.cycle_time_data_build import CycleTimeDataBuild
import random

from ob.planrunner.status import PlanStatus

logger = logging.getLogger(__name__.rsplit('.')[-1])


class NightPlan(BaseSequence):
    def __init__(self, id: str, sequence_dict: Dict[str, Any], telescope: 'Telescope',
                 info_callback: Dict[str, Callable], param: Dict[str, Any] or None = None) -> None:
        self.sequence_dict = sequence_dict
        self._r_id: int
        param = param if param is not None else {}
        param['plan_status'] = PlanStatus(telescope=telescope)
        super().__init__(id=id, name='NIGHTPLAN', info_callback=info_callback,
                         telescope=telescope, sequence_dict=sequence_dict, c_type='night_plan', param=param)
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self._cycle_time_data_build = None
        self._init_cycle_time()
        self._init_plan_status()
        self._write_subcomponents()
        self._set_r_id()

    def _init_cycle_time(self):
        self.param['cycle_time'] = self.telescope.get_cycle_time_calculator()
        self.param['cycle_time'].reset_time()
        self._get_rm_mode()
        self._get_altaz()
        self._cycle_time_data_build = CycleTimeDataBuild(
            telescope=self.telescope.id,
            base_folder=self.telescope.observatory.get_app_cfg(key='base_cycle_time_calc_dir'))

    def _init_plan_status(self):
        self.param['plan_status'].plan_static_publisher = self.get_publisher('plan_static')
        self.param['plan_status'].plan_status_publisher = self.get_publisher('plan_status')
        self.param['plan_status'].plan_time_publisher = self.get_publisher('plan_time')

    def _get_rm_mode(self):
        crm = self.camera.readoutmode
        if not isinstance(crm, int):
            crm = 0
        self.param['cycle_time'].set_start_rmode(rmode=crm)

    def _get_altaz(self):
        az = self.mount.azimuth
        alt = self.mount.altitude
        if not isinstance(az, float):
            az = 0.0
        if not isinstance(alt, float):
            alt = 45.0
        self.param['cycle_time'].set_telescope_start_az_alt(az=az, alt=alt)

    def _set_r_id(self) -> None:
        self._r_id =  round(self.get_julian_date(str(datetime.datetime.utcnow())), 2) * 100

    def _write_subcomponents(self):
        self.info_callback['stream_1'](f'{self.id} {self.name} written.')
        seq_id = 0
        sub = Sequence(id=f'{self.numb(seq_id)}', sequence_dict=self.sequence_dict,
                       telescope=self.telescope, info_callback=self.info_callback, param=self.param)
        self.subcomponents[f'{self.numb(seq_id)}'] = sub
        self.info_callback['stream_1'](f'Nightplan {self.id}'
                                       f' estimated time lenght: {self.param["cycle_time"].time_lenght_min}min')

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'{self.id} {self.name} started.')
        logger.info(f'Night plan {self.id} started')
        await self.journal.info(f'{self.id} {self.name} started,'
                                f' estimated time: {self.param["cycle_time"].time_lenght_min} min, '
                                f'utc finnish: {self.param["cycle_time"].finnish_time_utc}')
        self.info_callback['time_end'](f'{self.param["cycle_time"].finnish_time_utc}')
        self._set_r_id()
        self._cycle_time_data_build.insert_data(name='command_name', value=self.name)
        self._cycle_time_data_build.insert_data(name='telescope', value=self.telescope.id)
        self._cycle_time_data_build.insert_data(name='random_id', value=self._r_id)
        self._cycle_time_data_build.insert_data(name='started', value=True)
        self._cycle_time_data_build.save_to_log()
        d = self.telescope.get_dome()
        m = self.telescope.get_mount()
        skip = await self._arun(self.subcomponents, step_id=step_id)
        self._cycle_time_data_build.insert_data(name='done', value=self.done)
        self._cycle_time_data_build.insert_data(name='skipped', value=self.skipped)
        dome_az = await self.value_proof_get(name='dome_az', awaitab=d.aget_az, expect_type=float)
        mount_az = await self.value_proof_get(name='mount_az', awaitab=m.aget_az, expect_type=float)
        mount_alt = await self.value_proof_get(name='mount_alt', awaitab=m.aget_alt, expect_type=float)
        self._cycle_time_data_build.insert_data(name='dome_az_end', value=dome_az)
        self._cycle_time_data_build.insert_data(name='mount_az_end', value=mount_az)
        self._cycle_time_data_build.insert_data(name='mount_alt_end', value=mount_alt)
        self._cycle_time_data_build.save_to_log()
        self.info_callback['stream_5'](f'{self.id}')
        self.info_callback['stream_1'](f'{self.id} {self.name} done at: {str(datetime.datetime.utcnow())}')
        await self.journal.info(f'{self.id} {self.name} done at: {str(datetime.datetime.utcnow())}')
        logger.info(f'Night plan {self.id} completed')

        return skip

    def __del__(self):
        logger.info(f"Nightplan {self.id} deleted")
