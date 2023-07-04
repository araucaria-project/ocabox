import logging
from typing import List, Any, Dict
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.sequence import Sequence
from ob.planrunner.cycle_time_calc.cycle_time_data_build import  CycleTimeDataBuild
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
        self.args = []
        self.kwargs = {}
        self._r_id: int
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self._cycle_time_data_build = CycleTimeDataBuild(self.telescope.id)
        super().__init__(id=self.id, name=self.name, info_callback=self.info_callback,
                         observatory=self.parent.observatory, c_type='night_plan', kwargs=self.kwargs)
        self.info = {}
        #self._set_callb()
        self._write_subcomponents()
        self._set_r_id()

    def _set_r_id(self) -> None:
        self._r_id =  random.randint(0, 1000000)

    def _set_callb(self) -> None:
        self.info_callback['c_subcommands'] = self._build_nightplan_info_subcommands
        self.info_callback['c_commands'] = self._build_nightplan_info_commands
        self.info_callback['c_sequences'] = self._build_nightplan_info_sequences

    def _build_nightplan_info_subcommands(self, value: str) -> None:
        self._build_info_seq('subcommands', value)

    def _build_nightplan_info_commands(self, value: str) -> None:
        self._build_info_seq('commands', value)

    def _build_nightplan_info_sequences(self, value: str) -> None:
        self._build_info_seq('sequences', value)

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

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Night plan {self.id} started')
        logger.info(f'Night plan {self.id} started')
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
        self.info_callback['stream_1'](f'Night plan {self.id} completed')
        logger.info(f'Night plan {self.id} completed')
        return skip

    def __del__(self):
        logger.info(f"Nightplan {self.id} deleted")