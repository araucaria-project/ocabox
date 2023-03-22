import logging
from typing import Callable
from ob.planrunner.observ_plan import ObservPlan

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ObservPlanApi:

    def __init__(self, id: str, telescope: 'Telescope'):
        self.observ_plan = ObservPlan(observ_plan_id=id, telescope=telescope)
        super().__init__()

    def load_nightplan_string(self, nightplan_id: str, string: str, overwrite: bool = False):
        self.observ_plan.load_nightplan_string(nightplan_id=nightplan_id, string=string, overwrite=overwrite)

    def delete_nightplan(self, nightplan_id: str):
        self.observ_plan.delete_nightplan(nightplan_id=nightplan_id)

    def add_info_callback(self, name: str, info_callback: Callable) -> None:
        self.observ_plan.add_info_callback(name=name, info_callback=info_callback)

    def run_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        self.observ_plan.run_nightplan(nightplan_id=nightplan_id, step_id=step_id)

    def stop_nightplan(self) -> None:
        self.observ_plan.stop_nightplan()



