from ob.planrunner.observ_plan_api import ObservPlanApi
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger("observationplan")


class ObservationPlan:

    def __init__(self, id: str, telescope: 'Telescope'):
        self.observ = ObservPlanApi(id=id, telescope=telescope)

    def load_nightplan_string(self, nightplan_id: str, string: str, overwrite: bool = False):
        self.observ.load_nightplan_string(nightplan_id=nightplan_id, string=string, overwrite=overwrite)

    def delete_nightplan(self, nightplan_id: str):
        self.observ.delete_nightplan(nightplan_id=nightplan_id)

    def add_info_callback(self, name: str, info_callback: Callable) -> None:
        self.observ.add_info_callback(name=name, info_callback=info_callback)

    def run_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        """
        WARNING: Old sync method, do not use it, use arun_nightplan
        """
        self.observ.run_nightplan(nightplan_id=nightplan_id, step_id=step_id)

    def stop_nightplan(self) -> None:
        """
        WARNING: Old sync method, do not use it, use astop_nightplan
        """
        self.observ.stop_nightplan()

    async def arun_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        await self.observ.arun_nightplan(nightplan_id=nightplan_id, step_id=step_id)

    async def astop_nightplan(self) -> None:
        await self.observ.astop_nightplan()

    def get_nightplan_info(self, nightplan_id: str) -> Dict[Any, Any]:
        return self.observ.get_nightplan_info(nightplan_id=nightplan_id)

    def get_status(self, nightplan_id: str) -> Dict[Any, Any]:
        pass

