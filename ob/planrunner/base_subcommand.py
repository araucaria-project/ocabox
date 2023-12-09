import logging
from ob.planrunner.abstract_base import AbstractBase
from datetime import datetime
from typing import Dict, List, Any, Callable

logger = logging.getLogger(__name__.rsplit('.')[-1])


class BaseSubCommand(AbstractBase):

    def __init__(self, id: str, parent: 'Command', name: str, **kwargs) -> None:
        self.args = []
        self.kwargs = kwargs
        super().__init__(id=id, name=name, info_callback=parent.info_callback,
                         telescope=parent.telescope, c_type='subcommand', kwargs=self.kwargs)
        self._mk_folder(self.log_night_folder)
        self._create_sub_command_string()

    def _create_sub_command_string(self):
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
        self.info_callback['c_subcommands'](f'{self.id};{self.name};;{kw}')
        logger.debug(f'{self.id} is written')

    def exec_json(self, **kw) -> Dict[str, Any]:
        ex_js = {}
        if kw:
            if len(kw)>0:
                for n in kw.keys():
                    if n != 'seq_data':
                        ex_js[n] = kw[n]
        if self.kwargs:
            if len(self.kwargs) > 0:
                for n in self.kwargs.keys():
                    if n != 'seq_data':
                        ex_js[n] = self.kwargs[n]
        ex_js['id'] = self.id
        ex_js['name'] = self.name
        ex_js['started'] = self.started
        ex_js['done'] = self.done
        ex_js['skipped'] = self.skipped
        ex_js['timestamp_utc'] = str(datetime.utcnow())
        ex_js['c_type'] = self.c_type
        self._add_to_log_night(ex_js, {'c_type': 'command'})
        return ex_js

    async def arun(self) -> int:
        raise NotImplementedError
