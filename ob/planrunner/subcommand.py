import logging
logger = logging.getLogger(__name__.rsplit('.')[-1])
from typing import Dict, Any
from ob.planrunner.base_command import BaseCommand


class SubCommand(BaseCommand):

    def __init__(self, id: str, parent: 'Command', started: bool, done: bool, skipped: bool,
                 subcommand_name: str, **kwargs) -> None:
        self.id = id
        self.args = []
        self.kwargs = kwargs
        self.parent = parent
        self.subcommand_name = subcommand_name
        self.info_callback = parent.info_callback
        self.started = started
        self.done = done
        self.skipped = skipped
        self.observatory = parent.observatory
        self._create_command_string()
        self._mk_folder(self.log_night_folder)
        super().__init__(self.id, name=subcommand_name, info_callback=self.info_callback,
                         observatory=self.observatory, c_type='subcommand', kwargs=self.kwargs)

    def _create_command_string(self):
        kw = ''
        if len(self.args) > 0:
            for n in self.args:
                kw = f'{kw} {n}'
        w=0
        if len(self.kwargs) > 0:
            for n in self.kwargs.keys():
                if n != 'seq_data':
                    kw = f'{kw} {n}={self.kwargs[n]}'
                    w+=1
                #if w > 3: break
        self.info_callback['c_subcommands'](f'{self.id};{self.subcommand_name};;{kw}')
        logger.debug(f'{self.id} is written')

    async def arun(self) -> int:
        raise NotImplementedError
