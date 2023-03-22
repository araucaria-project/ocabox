import logging
from typing import List, Any, Callable
from ob.planrunner.coded_error import CantOverideNightPlanError
from ob.planrunner.night_plan import NightPlan
import logging
from typing import List, Any, Callable
import asyncio
from ob.planrunner.coded_error import CantOverideNightPlanError
from pyaraucaria.obs_plan.obs_plan_parser import ObsPlanParser


logger = logging.getLogger(__name__.rsplit('.')[-1])


class ObservPlan:

    def __init__(self, observ_plan_id: str, telescope: 'Telescope') -> None:
        self.observ_plan_id = observ_plan_id
        self.args = []
        self.kwargs = {}
        self.parent_args = []
        self.parent_kwargs = {}
        self.subcomponents = {}
        self.telescope = telescope
        self.parsed_plan: List[Any] or None = None
        self.plan_string: str or None = None
        self.tsk: asyncio.Task or None = None
        self.info_callback = {}
        self._set_defaut_info_callback()
        super().__init__()

    def _set_defaut_info_callback(self):
        self.add_info_callback('stream_1', logger.debug)
        self.add_info_callback('stream_2', logger.debug)
        self.add_info_callback('stream_3', logger.debug)
        self.add_info_callback('stream_4', logger.debug)
        self.add_info_callback('stream_5', logger.debug)
        self.add_info_callback('stream_6', logger.debug)

    def add_info_callback(self, name: str, info_callback: Callable) -> None:
        """
        Method set callback for plan runner information stream.
        :param name:
            stream_1 - current executing full name (all objects)
            stream_2 - subcommands written
            stream_3 - commands written
            stream_4 - sequences written
            stream_5 - finished id
            stream_6 -
        :param info_callback: set callback method
        :return: None
        """
        self.info_callback[name] = info_callback


    def delete_nightplan(self, nightplan_id: str) -> None:
        """
        Delete loaded night plan from observation plan.
        :param nightplan_id: Night plan id (default: julian night date)
        :return: None
        """
        if nightplan_id in self.subcomponents.keys():
            del self.subcomponents[nightplan_id]

    def get_nightplan(self, nightplan_id: str) -> None:
        try:
            return self.subcomponents[nightplan_id]
        except LookupError:
            logger.warning(f'There is no nightplan {nightplan_id}')
            self.info_callback['stream_1'](f'No nightplan {nightplan_id}')

    def write_nightplan(self, nightplan_id: str, nightplan_dict: List[Any], overwrite: bool = False) -> None:
        if (nightplan_id in self.subcomponents.keys()) and (overwrite is True):
            self.delete_nightplan(nightplan_id)
            np = NightPlan(nightplan_id, nightplan_dict, self)
            self.subcomponents[nightplan_id] = np
            logger.info(f'NightPlan {nightplan_id} to {self.observ_plan_id} is overwritten')
        elif (nightplan_id in self.subcomponents.keys()) and (overwrite is False):
            raise CantOverideNightPlanError
        else:
            np = NightPlan(nightplan_id, nightplan_dict, self)
            self.subcomponents[nightplan_id] = np
            logger.info(f'NightPlan {nightplan_id} to {self.observ_plan_id} is written')

    def load_nightplan_string(self, nightplan_id: str, string: str, overwrite: bool = False) -> None:
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
                self.write_nightplan(nightplan_id, self.parsed_plan, overwrite=overwrite)
                self.info_callback['stream_1'](f'Nightplan {nightplan_id} written')
            except CantOverideNightPlanError:
                logger.error(f'Cannot overwrite nightplan {nightplan_id}, please select overwrite=True')
                self.info_callback['stream_1'](f'Cannot overwrite nightplan {nightplan_id}, please select overwrite=True')
        else:
            logger.error(f'Plan is parsed wrong. Check the syntax.')
            self.info_callback['stream_1'](f'Plan is parsed wrong. Check the syntax. No plan is written')

    def _parse_plan(self) -> None:
        if self.plan_string:
            parser = ObsPlanParser()
            try:
                self.parsed_plan = parser.convert_from_string(self.plan_string)
                logger.debug(f'Parsed: {self.parsed_plan}')
            except Exception as e:
                self.info_callback['stream_1'](f'Cannot parse plan - please check the syntax')
                logger.error(f'Cannot parse plan - please check the syntax')
        else:
            logger.error(f'No plan to parse.')

    def run_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        """
        Method run night plan.
        :param nightplan_id:  Night plan id (default: julian night date)
        :param step_id: optional, run from specified step, example: '00' or '00_01_02' or '00_02'
        :return: None
        """
        self.stop_nightplan()
        if self.get_nightplan(nightplan_id):
            if self.tsk is None:
                self.tsk = asyncio.create_task(self.arun_night(nightplan_id, step_id=step_id))

    def stop_nightplan(self) -> None:
        """
        Method stops night plan.
        :return: None
        """
        if self.tsk:
            self.tsk.cancel()
            self.info_callback['stream_1'](f'Nightplan stopped')
            self.tsk = None
        self.tsk = None

    async def arun_night(self, nightplan_id: str, step_id: str or None = None) -> None:
        await self.subcomponents[nightplan_id].arun(step_id=step_id)
