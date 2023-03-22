from ob.planrunner.observ_plan_api import ObservPlanApi
import logging
from typing import Callable

logger = logging.getLogger("observationplan")


class ObservationPlan:

    def __init__(self, id: str, telescope: 'Telescope'):
        self.plan_runner = ObservPlanApi(id=id, telescope=telescope)

    def load_nightplan_string(self, nightplan_id: str, string: str, overwrite: bool = False):
        self.plan_runner.load_nightplan_string(nightplan_id=nightplan_id, string=string, overwrite=overwrite)

    def delete_nightplan(self, nightplan_id: str):
        self.plan_runner.delete_nightplan(nightplan_id=nightplan_id)

    def add_info_callback(self, name: str, info_callback: Callable) -> None:
        self.plan_runner.add_info_callback(name=name, info_callback=info_callback)

    def run_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        self.plan_runner.run_nightplan(nightplan_id=nightplan_id, step_id=step_id)

    def stop_nightplan(self) -> None:
        self.plan_runner.stop_nightplan()
