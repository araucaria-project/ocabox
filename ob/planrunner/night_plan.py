import logging
from typing import List, Any
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.sequence import Sequence


logger = logging.getLogger(__name__.rsplit('.')[-1])


class NightPlan(AbstractSequence):
    def __init__(self, id: str, sequence_dict: List[Any], parent: 'ObservationPlan') -> None:
        self.id = id
        self.name = 'Night plan'
        self.parent = parent
        self.sequence_dict = sequence_dict
        self.subcomponents = {}
        self.telescope = parent.telescope
        self.info_callback = parent.info_callback
        self.args = []
        self.kwargs = {}
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        super().__init__(self.id, self.name, self.info_callback, observatory=self.parent.observatory)
        self.info = {}
        #self._set_callb()
        self._write_subcomponents()

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
        for se in self.sequence_dict:
            sub = Sequence(f'{self.numb(seq_id)}', se, self)
            self.subcomponents[f'{self.numb(seq_id)}'] = sub
            seq_id += 1

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Night plan {self.id} started')
        logger.info(f'Night plan {self.id} started')
        skip = await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_5'](f'{self.id}')
        self.info_callback['stream_1'](f'Night plan {self.id} completed')
        logger.info(f'Night plan {self.id} completed')
        return skip

    def __del__(self):
        logger.info(f"Nightplan {self.id} deleted")