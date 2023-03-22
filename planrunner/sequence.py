from typing import Dict, Any
import logging
from planrunner.abstract_sequence import AbstractSequence
from planrunner.command import Command
from planrunner.coded_error import SequenceTreeError


log = logging.getLogger(__name__.rsplit('.')[-1])


class Sequence(AbstractSequence):

    def __init__(self, id: str, sequence_dict: Dict[Any, Any],
                 parent: 'NightPlan' or 'Sequence') -> None:
        self.id = id
        self.sequence_dict = sequence_dict
        self.parent = parent
        self.args = self.build_args(self.sequence_dict)
        self.kwargs = self.build_kwargs(self.sequence_dict)
        self.parent_args = self.parent.args + self.parent.parent_args
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self.subcomponents = {}
        self.telescope = parent.telescope
        self.info_callback = parent.info_callback
        super().__init__()
        self._create_sequence_string()
        self.build_sequence()

    def _create_sequence_string(self):
        kw = ''
        for n in self.args:
            kw = f'{kw} {n}'
        for n in self.kwargs.keys():
            kw = f'{kw} {n}={self.kwargs[n]}'
        for n in self.parent_kwargs.keys():
            kw = f'{kw} {n}={self.parent_kwargs[n]}'
        self.info_callback['stream_4'](f'{self.id} SEQUENCE {kw}')

    def build_sequence(self) -> None:
        id_next = 0
        if 'all_commands' in self.sequence_dict.keys():
            for case in self.sequence_dict['all_commands']:
                if 'begin_sequence' in case.keys():
                    sub = self.write_subcomponent(f'{self.id}_{self.numb(id_next)}',case)
                    self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                    id_next += 1
                elif 'command_name' in case.keys():
                    com = self.write_command(f'{self.id}_{self.numb(id_next)}', case)
                    self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = com
                    id_next += 1
                else:
                    raise SequenceTreeError(Exception)

    def write_subcomponent(self, sequence_id, sequence_dict) -> 'Sequence':
        sub = Sequence(sequence_id, sequence_dict, self)
        log.info(f'Sequence {sequence_id} to {self.id} is written')
        return sub

    def write_command(self, command_id, command_dict) -> 'Command':
        com = Command(command_id, command_dict, self)
        log.info(f'Command {command_id} to {self.id} is written')
        return com

    async def arun(self, step_id: str or None = None) -> None:
        self.info_callback['stream_1'](f'Sequence {self.id} started')
        await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_1'](f'Sequence {self.id} done')
        self.info_callback['stream_5'](f'{self.id}')

