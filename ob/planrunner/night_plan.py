import logging
from typing import List, Any
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.sequence import Sequence


log = logging.getLogger(__name__.rsplit('.')[-1])


class NightPlan(AbstractSequence):
    def __init__(self, id: str, sequence_dict: List[Any], parent: 'ObservationPlan') -> None:
        self.id = id
        self.parent = parent
        self.sequence_dict = sequence_dict
        self.subcomponents = {}
        self.args = []
        self.kwargs = {}
        self.parent_args = []
        self.parent_kwargs = {}
        self.telescope = parent.telescope
        self.info_callback = parent.info_callback
        super().__init__()
        self._write_subcomponents()

    def _write_subcomponents(self):
        seq_id = 0
        for se in self.sequence_dict:
            sub = self._write_subcomponent(f'{self.numb(seq_id)}', se)
            self.subcomponents[f'{self.numb(seq_id)}'] = sub
            seq_id += 1

    def _write_subcomponent(self, sequence_id, sequence_dict) -> 'Sequence':
        sub = Sequence(sequence_id, sequence_dict, self)
        log.info(f'Sequence {sequence_id} to {self.id} is written')
        return sub

    async def arun(self, step_id: str or None = None) -> None:
        self.info_callback['stream_1'](f'Nightplan {self.id} started')
        await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_1'](f'Nightplan {self.id} done')
        self.info_callback['stream_5'](f'{self.id}')

    def __del__(self):
        log.info(f"Nightplan {self.id} deleted")