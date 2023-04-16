import logging
import time
logger = logging.getLogger(__name__.rsplit('.')[-1])
from typing import Dict, Any
from datetime import datetime

class SubCommand:

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
        super().__init__()
        self._create_command_string()

    def _create_command_string(self):
        kw = ''
        for n in self.args:
            kw = f'{kw} {n}'
        w=0
        for n in self.kwargs.keys():
            kw = f'{kw} {n}={self.kwargs[n]}'
            w+=1
            if w > 3: break
        self.info_callback['c_subcommands'](f'{self.id};{self.subcommand_name};{kw}')
        logger.info(f'Subcommand {self.id} name: {self.subcommand_name} is written')

    async def arun(self) -> int:
        raise NotImplementedError

    async def stop_nightplan(self, message: str = '') -> None:
        self.info_callback['stream_1'](f'Nightplan stopping: {message}')
        logger.info(f'Nightplan stopped {message}')
        await self.parent.stop()

    async def subcommand_timeout(self, t_start: float, subc_timeout: float = 600) -> int:
        t_stamp = time.time()
        if t_stamp > t_start + subc_timeout:
            return 1

    def exec_json(self, **kw) -> Dict[str, Any]:
        ex_js = {}
        if kw:
            for n in kw.keys():
                ex_js[n] = kw[n]
        if self.kwargs:
            for n in self.kwargs.keys():
                ex_js[n] = self.kwargs[n]
        ex_js['id'] = self.id
        ex_js['name'] = self.subcommand_name
        ex_js['started'] = self.started
        ex_js['done'] = self.done
        ex_js['skipped'] = self.skipped
        ex_js['timestamp_utc'] = str(datetime.utcnow())
        return ex_js

    @staticmethod
    def proof_val(value: Any) -> Any:
        try:
            return value
        except:
            try:
                return value
            except:
                return ''