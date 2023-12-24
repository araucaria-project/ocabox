from typing import Dict, List, Any, Callable
import logging
from ob.planrunner.abstract_base import AbstractBase
from ob.planrunner.coded_error import SequenceTreeError
from ob.planrunner.status import PlanStatusEnum

logger = logging.getLogger(__name__.rsplit('.')[-1])


class BaseSequence(AbstractBase):

    def __init__(self, id: str, name: str, telescope: 'Telescope', sequence_dict: Dict[str, Any],
                 info_callback: Dict[str, Callable], c_type: str, param: Dict[str, Any]) -> None:

        self.subcomponents = {}
        self.sequence_dict = sequence_dict
        self.args: List = []
        self.kwargs: Dict = {}
        super().__init__(id=id, name=name, telescope=telescope,
                         info_callback=info_callback, c_type=c_type, param=param)

    def build_args(self, sequence_dict: Dict[Any, Any]) -> None:
        if 'args' in sequence_dict.keys():
            self.args = sequence_dict['args']
        else:
            self.args = []
        self.param['plan_status'].upd_static_args(id=self.id, args_list=self.args)

    def build_kwargs(self, sequence_dict: Dict[str, Any]) -> None:
        if 'kwargs' in sequence_dict.keys():
            for n, m in sequence_dict['kwargs'].items():
                if n in self.KWARGS:
                    pass
                else:
                    self.info_callback['stream_1'](f'Warning: {self.id} kwarg:{n} wrong name')
                    logger.error(f'{self.id} kwarg:{n} not in allowed list.')
            self.kwargs = sequence_dict['kwargs']
            self.param['plan_status'].upd_static_kwargs(id=self.id, value=self.kwargs)
        else:
            self.kwargs = {}

    @staticmethod
    def numb(number: int) -> str:
        return f'{number:02d}'

    async def _arun(self, subcomponents: Any, step_id: str or None = None) -> int:
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        self.info_callback['exec_json'](self.exec_json(**self.kwargs))
        if self.c_type == 'command':
            for c in subcomponents:
                if step_id is not None:
                    if step_id[: len(subcomponents[c].id)] <= subcomponents[c].id:
                        c.param['plan_status'].upd_status(id=c.id, value=PlanStatusEnum.loaded)
                else:
                    c.param['plan_status'].upd_status(id=c.id, value=PlanStatusEnum.loaded)
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
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                self.info_callback['exec_json'](self.exec_json(**self.kwargs))
                return 0
            if skip == 2:
                self.skipped = True

                if self.name == 'STOP':
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
                else:
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)

                self.info_callback['exec_json'](self.exec_json(**self.kwargs))
                return 2
        # self.info_callback['stream_1'](f'{self.name} {self.id} done')
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(**self.kwargs))
        return 0
