from typing import Dict, List, Any, Callable
import logging
from datetime import datetime

logger = logging.getLogger(__name__.rsplit('.')[-1])


class AbstractSequence:

    def __init__(self, id: str, name: str, info_callback: Dict[str, Callable], observatory) -> None:
        self.id = id
        self.observatory = observatory
        self.info_callback = info_callback
        self.name = name
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__()

    @staticmethod
    def build_args(sequence_dict: Dict[Any, Any]) -> List[Any]:
        if 'args' in sequence_dict.keys():
            return sequence_dict['args']
        else:
            return []

    @staticmethod
    def build_kwargs(sequence_dict: Dict[Any, Any]) -> Dict[Any, Any]:
        if 'kwargs' in sequence_dict.keys():
            return sequence_dict['kwargs']
        else:
            return {}

    @staticmethod
    def numb(number: int) -> str:
        return f'{number:02d}'

    async def _arun(self, subcomponents: Any, step_id: str or None = None) -> int:
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        for n in subcomponents.keys():
            skip = 0
            if step_id is None:
                skip = await subcomponents[n].arun(step_id=step_id)
            else:
                match = step_id[: len(subcomponents[n].id)]
                if match <= subcomponents[n].id:
                    skip = await subcomponents[n].arun(step_id=step_id)
            if skip > 0:
                self.info_callback['stream_1'](f'{self.id} skipped')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                return 1
        self.info_callback['stream_1'](f'{self.name} {self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0

    def exec_json(self) -> Dict[str, Any]:
        ex_js = {}
        ex_js['id'] = self.id
        ex_js['name'] = self.name
        ex_js['started'] = self.started
        ex_js['done'] = self.done
        ex_js['skipped'] = self.skipped
        ex_js['timestamp_utc'] = str(datetime.utcnow())
        return ex_js