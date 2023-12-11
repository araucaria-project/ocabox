from typing import Dict, Any, Callable
import logging
from ob.planrunner.base_sequence import BaseSequence
from ob.planrunner.command import Command
from ob.planrunner.coded_error import SequenceTreeError


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Sequence(BaseSequence):

    def __init__(self, id: str, sequence_dict: Dict[str, Any], telescope: 'Telescope',
                 info_callback: Dict[str, Callable], param: Dict[str, Any] or None = None) -> None:
        super().__init__(id=id, name='SEQUENCE', info_callback=info_callback,
                         telescope=telescope, sequence_dict=sequence_dict, c_type='sequence', param=param)
        self.build_args(self.sequence_dict)
        self.build_kwargs(sequence_dict=self.sequence_dict)
        self.build_sequence()

    def _create_sequence_string(self):
        kw = ''
        for n in self.kwargs.keys():
            kw = f'{kw} {n}={self.kwargs[n]}'
        self.info_callback['c_sequences'](f'{self.id};SEQUENCE;;{kw}')
        logger.info(f'{self.id} is written')

    def build_sequence(self) -> None:
        self._create_sequence_string()
        id_next = 0
        if 'subcommands' in self.sequence_dict.keys():
            for case in self.sequence_dict['subcommands']:
                if 'command_name' in case.keys():
                    if case['command_name'] in self.COMMAND_NAMES:
                        if case['command_name'] == 'SEQUENCE':
                            sub = self.write_subcomponent(f'{self.id}_{self.numb(id_next)}',case)
                            self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                            id_next += 1
                        else:
                            com = self.write_command(f'{self.id}_{self.numb(id_next)}', case)
                            self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = com
                            id_next += 1
                    else:
                        self.info_callback['stream_1'](f'Wrong command name {case["command_name"]}')
                        logger.warning(f'Wrong command name {case["command_name"]}')
                        raise SequenceTreeError
                else:
                    raise SequenceTreeError

    def write_subcomponent(self, sequence_id, sequence_dict) -> 'Sequence':
        sub = Sequence(id=sequence_id, sequence_dict=sequence_dict, telescope=self.telescope,
                       info_callback=self.info_callback, param=self.param)
        return sub

    def write_command(self, command_id, command_dict) -> 'Command':
        com = Command(id=command_id, sequence_dict=command_dict, telescope=self.telescope,
                       info_callback=self.info_callback, param=self.param)
        return com

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Sequence {self.id} started')
        await self.journal.debug(f'{self.id} {self.name} started.')
        logger.info(f'{self.id} started')
        skip = await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_5'](f'{self.id}')
        await self.journal.debug(f'{self.id} {self.name} done.')
        logger.info(f'{self.id} done')
        return skip
