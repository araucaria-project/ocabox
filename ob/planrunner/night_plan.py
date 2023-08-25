import datetime
import logging
from typing import List, Any, Dict
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.sequence import Sequence
from ob.planrunner.cycle_time_calc.cycle_time_data_build import CycleTimeDataBuild
from ob.planrunner.cycle_time_calc.cycle_time_calc import CycleTimeCalc
from ob.planrunner.cycle_time_calc.cycle_time_data_clean import CycleTimeDataClean
from ob.planrunner.cycle_time_calc.cycle_time_train import CycleTimeTrain
import random


logger = logging.getLogger(__name__.rsplit('.')[-1])


class NightPlan(AbstractSequence):
    def __init__(self, id: str, sequence_dict: Dict[str, Any],
                 parent: 'ObservationPlan', param: Dict[str, Any] or None = None) -> None:
        self.id = id
        self.name = 'Night plan'
        self.parent = parent
        self.sequence_dict = sequence_dict
        self.subcomponents = {}
        self.telescope = parent.telescope
        self.info_callback = parent.info_callback
        self.param = param if param is not None else {}
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self.param['cycle_time'] = CycleTimeCalc(self.telescope.id)
        self._get_rm_mode()
        self._get_altaz()
        self.args = []
        self.kwargs = {}
        self._r_id: int
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self._cycle_time_data_build = CycleTimeDataBuild(self.telescope.id)

        super().__init__(id=self.id, name=self.name, info_callback=self.info_callback,
                         observatory=self.parent.observatory, c_type='night_plan', kwargs=self.kwargs)
        self.info = {}
        self._write_subcomponents()
        self._set_r_id()

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
        self._r_id =  random.randint(0, 1000000)

    def _build_info_seq(self, name: str, value: str):
        if name in self.info.keys():
            self.info[name] = self.info[name] + [value]
        else:
            self.info[name] = []
            self.info[name] = self.info[name] + [value]

    def _write_subcomponents(self):
        self.info_callback['stream_1'](f'Nightplan {self.id} written')
        seq_id = 0
        sub = Sequence(f'{self.numb(seq_id)}', self.sequence_dict, self, param=self.param)
        self.subcomponents[f'{self.numb(seq_id)}'] = sub
        self.info_callback['stream_1'](f'Nightplan {self.id}'
                                       f' estimated time lenght: {self.param["cycle_time"].time_lenght_min}min')

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Night plan {self.id} started')
        logger.info(f'Night plan {self.id} started')
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
        self.info_callback['stream_1'](f'Night plan {self.id} completed at: {str(datetime.datetime.utcnow())}')
        logger.info(f'Night plan {self.id} completed')
        if skip == 0:
            CycleTimeDataClean.data_clean_all()
            CycleTimeTrain.train_all_telesc_all_commands()
        return skip

    def __del__(self):
        logger.info(f"Nightplan {self.id} deleted")
