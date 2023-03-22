import logging
from typing import List, Any
from planrunner.coded_error import CantOverideNightPlanError
from planrunner.night_plan import NightPlan


log = logging.getLogger(__name__.rsplit('.')[-1])


class ObservationPlan:

    def __init__(self, client_name: str, observ_plan_id: str,
                 telescope: 'Telescope') -> None:

        self.observ_plan_id = observ_plan_id
        self.client_name = client_name
        self.subcomponents = {}
        self.telescope = telescope
        self.info_callback = {}
        super().__init__()
        self.run_start = False

    def delete_nightplan(self, nightplan_id: str) -> None:
        if nightplan_id in self.subcomponents.keys():
            del self.subcomponents[nightplan_id]

    def get_nightplan(self, nightplan_id: str) -> None:
        try:
            return self.subcomponents[nightplan_id]
        except LookupError:
            log.warning(f'There is no nightplan {nightplan_id}')
            self.info_callback['stream_1'](f'No nightplan {nightplan_id}')

    def write_nightplan(self, nightplan_id: str, nightplan_dict: List[Any], overwrite: bool = False) -> None:
        if (nightplan_id in self.subcomponents.keys()) and (overwrite is True):
            self.delete_nightplan(nightplan_id)
            np = NightPlan(nightplan_id, nightplan_dict, self)
            self.subcomponents[nightplan_id] = np
            log.info(f'NightPlan {nightplan_id} to {self.observ_plan_id} is overwritten')
        elif (nightplan_id in self.subcomponents.keys()) and (overwrite is False):
            raise CantOverideNightPlanError
        else:
            np = NightPlan(nightplan_id, nightplan_dict, self)
            self.subcomponents[nightplan_id] = np
            log.info(f'NightPlan {nightplan_id} to {self.observ_plan_id} is written')

    async def arun_night(self, nightplan_id: str, step_id: str or None = None) -> None:
        await self.subcomponents[nightplan_id].arun(step_id=step_id)
