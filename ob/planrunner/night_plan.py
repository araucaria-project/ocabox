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
        self.param = param
        self.mount = self.telescope.get_mount()
        self.camera = self.telescope.get_camera()
        self.param['cycle_time'] = CycleTimeCalc(self.telescope.id)
        self.param['cycle_time'].set_telescope_start_az_alt(az=self.mount.azimuth, alt=self.mount.altitude)
        self.param['cycle_time'].set_start_rmode(rmode=self.camera.readoutmode)
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
                                       f' time lenght: {self.param["cycle_time"].time_lenght_min}min')

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Night plan {self.id} started')
        logger.info(f'Night plan {self.id} started')
        self.info_callback['time_end'](f'{self.param["cycle_time"].finnish_time_from_now_utc()}')
        self._set_r_id()
        self._cycle_time_data_build.insert_data(name='command_name', value=self.name)
        self._cycle_time_data_build.insert_data(name='telescope', value=self.telescope.id)
        self._cycle_time_data_build.insert_data(name='random_id', value=self._r_id)
        self._cycle_time_data_build.insert_data(name='started', value=True)
        self._cycle_time_data_build.save_to_log()
        skip = await self._arun(self.subcomponents, step_id=step_id)
        d = self.telescope.get_dome()
        m = self.telescope.get_mount()
        self._cycle_time_data_build.insert_data(name='done', value=self.done)
        self._cycle_time_data_build.insert_data(name='skipped', value=self.skipped)
        self._cycle_time_data_build.insert_data(name='dome_az_end', value=await d.aget_az())
        self._cycle_time_data_build.insert_data(name='mount_az_end', value=await m.aget_az())
        self._cycle_time_data_build.insert_data(name='mount_alt_end', value=await m.aget_alt())
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