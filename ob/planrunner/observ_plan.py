from ob.planrunner.night_plan import NightPlan
import logging
from typing import List, Any, Callable, Dict
import asyncio
from ob.planrunner.coded_error import CantOverideNightPlanError, SequenceTreeError
from pyaraucaria.obs_plan.obs_plan_parser import ObsPlanParser

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ObservPlan:

    def __init__(self, observ_plan_id: str, telescope: 'Telescope') -> None:
        self.observ_plan_id = observ_plan_id
        self.args = []
        self.kwargs = {}
        self.parent_kwargs = {}
        self.subcomponents = {}
        self.telescope = telescope
        self.observatory = telescope.observatory
        self.parsed_plan: List[Any] or None = None
        self.plan_string: str or None = None
        self.tsk: asyncio.Task or None = None
        self.info_callback = {}
        self.callbacks_dict = {}
        self.running_nightplan: str or None = None
        self.add_callbacks()
        self.create_callb_dict()
        super().__init__()

    def create_callb_dict(self):
        self.callbacks_dict['stream_1'] = [self.empty_callback]
        self.callbacks_dict['stream_5'] = [self.empty_callback]
        self.callbacks_dict['c_subcommands'] = [self.empty_callback]
        self.callbacks_dict['c_commands'] = [self.empty_callback]
        self.callbacks_dict['c_sequences'] = [self.empty_callback]
        self.callbacks_dict['exec_json'] = [self.empty_callback]
        self.callbacks_dict['time_end'] = [self.empty_callback]

    def empty_callback(self, value):
        pass

    def get_nightplan_info(self, nightplan_id: str) -> Dict[Any, Any]:
        return self.get_nightplan(nightplan_id).info

    def add_info_callback(self, name: str, info_callback: Callable):
        self.callbacks_dict[name] = [info_callback]

    def stream_5_callback(self, value):
        for calb in self.callbacks_dict['stream_5']:
            calb(value)

    def stream_1_callback(self, value):
        for calb in self.callbacks_dict['stream_1']:
            calb(value)

    def c_subcommands_callback(self, value):
        for calb in self.callbacks_dict['c_subcommands']:
            calb(value)

    def c_commands_callback(self, value):
        for calb in self.callbacks_dict['c_commands']:
            calb(value)

    def c_sequences_callback(self, value):
        for calb in self.callbacks_dict['c_sequences']:
            calb(value)

    def exec_json_callback(self, value):
        for calb in self.callbacks_dict['exec_json']:
            calb(value)

    def time_end_callback(self, value):
        for calb in self.callbacks_dict['time_end']:
            calb(value)

    def add_callbacks(self) -> None:
        """
        Method set callback for plan runner information stream.
        :param name:
            stream_1 - current executing full name (all objects)
            c_subcommands - subcommands written
            c_commands - commands written
            c_sequences - sequences written
            stream_5 - finished id
            exec_json - current executing json format
        :param info_callback: set callback method
        :return: None
        """
        self.info_callback['stream_5'] = self.stream_5_callback
        self.info_callback['stream_1'] = self.stream_1_callback
        self.info_callback['c_subcommands'] = self.c_subcommands_callback
        self.info_callback['c_commands'] = self.c_commands_callback
        self.info_callback['c_sequences'] = self.c_sequences_callback
        self.info_callback['exec_json'] = self.exec_json_callback
        self.info_callback['time_end'] = self.time_end_callback

    def delete_nightplan(self, nightplan_id: str) -> None:
        """
        Delete loaded night plan from observation plan.
        :param nightplan_id: Night plan id (default: julian night date)
        :return: None
        """
        if nightplan_id in self.subcomponents.keys():
            del self.subcomponents[nightplan_id]

    def get_nightplan(self, nightplan_id: str) -> NightPlan or None:
        try:
            return self.subcomponents[nightplan_id]
        except LookupError:
            logger.warning(f'There is no night plan {nightplan_id}')

    def write_nightplan(self, nightplan_id: str, nightplan_dict: Dict[str, Any],
                        overwrite: bool = False, param: Dict[str, Any] or None = None) -> None:
        if (nightplan_id in self.subcomponents.keys()) and (overwrite is True):
            self.delete_nightplan(nightplan_id)
            np = NightPlan(nightplan_id, nightplan_dict, self, param=param)
            self.subcomponents[nightplan_id] = np
            logger.info(f'Night plan {nightplan_id} to {self.observ_plan_id} is overwritten')

        elif (nightplan_id in self.subcomponents.keys()) and (overwrite is False):
            raise CantOverideNightPlanError

        else:
            np = NightPlan(nightplan_id, nightplan_dict, self, param=param)
            self.subcomponents[nightplan_id] = np
            logger.info(f'Night plan {nightplan_id} is written')

    def load_nightplan_string(self, nightplan_id: str, string: str,
                              overwrite: bool = False, param: Dict[str, Any] or None = None) -> None:
        """
        :param nightplan_id: Night plan id (default: julian night date)
        :param string:
        :param overwrite: if false night plan not be written
        :return:
        """
        # TODO keep nightplans in settings, only load plans for night, else delete from memory.
        self.plan_string = string
        self._parse_plan()
        if self.parsed_plan is not None:
            try:
                self.write_nightplan(nightplan_id, self.parsed_plan, overwrite=overwrite, param=param)
            except CantOverideNightPlanError:
                logger.warning(f'Cannot overwrite night plan {nightplan_id}, please select overwrite=True')
                self.info_callback['stream_1'](f'Cannot overwrite night plan {nightplan_id},'
                                               f' please select overwrite=True')
            except SequenceTreeError:
                logger.warning(f'Plan is wrong. Check the syntax.')
                self.info_callback['stream_1'](f'Warning: Plan have syntax errors.')

    def _parse_plan(self) -> None:
        if self.plan_string:
            try:
                self.parsed_plan = ObsPlanParser.convert_from_string(self.plan_string)
                logger.debug(f'Parsed: {self.parsed_plan}')
            except Exception as e:
                logger.error(f'Cannot parse plan - please check the syntax')
        else:
            logger.error(f'No plan to parse.')

    def run_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        """
        WARNING: Old sync method, do not use it
        """
        self.stop_nightplan()
        if self.get_nightplan(nightplan_id):
            if self.tsk is None:
                self.running_nightplan = nightplan_id
                self.tsk = asyncio.create_task(self.arun_night(nightplan_id, step_id=step_id))

    def stop_nightplan(self) -> None:
        """
        WARNING: Old sync method, do not use it
        """
        if self.tsk:
            self.tsk.cancel()
            logger.info(f'Night plan stopped')
            self.info_callback['stream_1'](f'Night plan stopped')
            self.tsk = None
        self.tsk = None
        self.running_nightplan = None

    def get_loop(self) -> Any or None:
        try:
            loop = asyncio.get_event_loop()
            return loop
        except RuntimeError:
            logger.error("There is no running asyncio loop")
            return None

    async def arun_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        """
        Async method run night plan.
        :param nightplan_id:  Night plan id
        :param step_id: optional, run from specified step, example: '00' or '00_01_02' or '00_02'
        :return: None
        """
        await self.astop_nightplan()
        if self.get_nightplan(nightplan_id):
            if self.tsk is None:
                self.running_nightplan = nightplan_id
                if self.running_nightplan in self.subcomponents.keys():
                    self.subcomponents[self.running_nightplan].started = True
                    self.subcomponents[self.running_nightplan].skipped = False
                    self.subcomponents[self.running_nightplan].done = False
                loop = self.get_loop()
                if loop:
                    self.tsk = loop.create_task(self.arun_night(nightplan_id, step_id=step_id))
                else:
                    logger.error(f"Can't run night plan, no loop")
                    self.info_callback['stream_1'](f"Can't run night plan, no loop")

    async def astop_nightplan(self) -> None:
        """
        Async method stops night plan.
        :return: None
        """
        if self.tsk:
            self.tsk.cancel()
            logger.info(f'Night plan stopped')
            self.info_callback['stream_1'](f'Night plan stopped')
            self.tsk = None
        self.tsk = None
        if self.running_nightplan in self.subcomponents.keys():
            self.subcomponents[self.running_nightplan].skipped = True
        self.running_nightplan = None

    async def arun_night(self, nightplan_id: str, step_id: str or None = None) -> None:
        await self.subcomponents[nightplan_id].arun(step_id=step_id)

    async def stop(self):
        await self.astop_nightplan()

    def is_nightplan_running(self, nightplan_id: str) -> bool:
        if nightplan_id in self.subcomponents.keys():
            if self.subcomponents[nightplan_id].started is True:
                if self.subcomponents[nightplan_id].done is True or self.subcomponents[nightplan_id].skipped is True:
                    return False
                else:
                    return True
        return False
