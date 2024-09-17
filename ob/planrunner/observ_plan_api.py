import logging
from typing import Callable, Dict, List, Any
from ob.planrunner.observ_plan import ObservPlan
from ob.planrunner.config_general import ConfigGeneral


logger = logging.getLogger(__name__.rsplit('.')[-1])


class ObservPlanApi:

    def __init__(self, id: str, telescope: 'Telescope') -> None:
        self.telescope = telescope
        self.observ_plan = ObservPlan(observ_plan_id=id, telescope=telescope)
        super().__init__()

    def load_nightplan_string(self, nightplan_id: str, string: str,
                              overwrite: bool = False, param: Dict[str, Any] or None = None) -> None:
        self.observ_plan.load_nightplan_string(nightplan_id=nightplan_id,
                                               string=string, overwrite=overwrite, param=param)

    def delete_nightplan(self, nightplan_id: str) -> None:
        self.observ_plan.delete_nightplan(nightplan_id=nightplan_id)

    def add_info_callback(self, name: str, info_callback: Callable) -> None:
        # TODO to change/delete
        self.observ_plan.add_info_callback(name=name, info_callback=info_callback)

    def get_nightplan_info(self, nightplan_id: str) -> Dict[Any, Any]:
        # TODO develop
        return self.observ_plan.get_nightplan_info(nightplan_id=nightplan_id)

    def run_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        """
        WARNING: Old sync method, do not use it
        """
        self.observ_plan.run_nightplan(nightplan_id=nightplan_id, step_id=step_id)

    def stop_nightplan(self) -> None:
        """
        WARNING: Old sync method, do not use it
        """
        self.observ_plan.stop_nightplan()

    async def arun_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        await self.observ_plan.arun_nightplan(nightplan_id=nightplan_id, step_id=step_id)

    async def astop_nightplan(self) -> None:
        await self.observ_plan.astop_nightplan()

    def is_nightplan_running(self, nightplan_id: str) -> bool:
        return self.observ_plan.is_nightplan_running(nightplan_id=nightplan_id)

    async def aload_nightplan_string(self, nightplan_id: str, string: str,
                                     overwrite: bool = False, param: Dict[str, Any] or None = None,
                                     client_config_dict: Dict or None = None) -> bool:
        if client_config_dict is not None and isinstance(client_config_dict, Dict):
            logger.info('Gathered client config dict')
            if not isinstance(param, Dict):
                param = {}
            param['cfg_gen'] = ConfigGeneral(telescope=self.telescope, client_config_dict=client_config_dict)
        return await self.observ_plan.aload_nightplan_string(
            nightplan_id=nightplan_id, string=string, overwrite=overwrite, param=param
        )
