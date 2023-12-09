from typing import Dict, List, Any, Callable
import logging
from ob.planrunner.base_command import BaseCommand
from ob.planrunner.coded_error import SequenceTreeError


logger = logging.getLogger(__name__.rsplit('.')[-1])


class AbstractSequence(BaseCommand):

    def __init__(self, id: str, name: str, telescope: 'Telescope', info_callback: Dict[str, Callable],
                 c_type: str, kwargs) -> None:
        # self.args: List = args
        self.kwargs: Dict = kwargs
        super().__init__(id=id, name=name, info_callback=info_callback,
                         telescope=telescope, c_type=c_type, kwargs=self.kwargs)

    @staticmethod
    def build_args(sequence_dict: Dict[Any, Any]) -> List[Any]:
        if 'args' in sequence_dict.keys():
            return sequence_dict['args']
        else:
            return []

    def build_kwargs(self, sequence_dict: Dict[str, Any],
                     info_callback: Dict[str, Any] or None = None,
                     id: str or None = None) -> Dict[str, Any]:
        if 'kwargs' in sequence_dict.keys():
            for n, m in sequence_dict['kwargs'].items():
                if n in self.KWARGS:
                    pass
                else:
                    if info_callback:
                        info_callback['stream_1'](f'Warning: {id} kwarg:{n} wrong name')
                    logger.warning(f'{id} kwarg:{n} wrong name')
                    raise SequenceTreeError
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
            if skip == 1:
                self.info_callback['stream_1'](f'{self.id} skipped')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                return 0
            if skip == 2:
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                return 2
        # self.info_callback['stream_1'](f'{self.name} {self.id} done')
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0
