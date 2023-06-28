import logging
from abc import ABC, abstractmethod

from ob.data_colection.resource_manager.resource_manager import ResourceManager
from ob.planrunner.ern.plan_task_manager_protocol import PlanTaskManagerProtocol

logger = logging.getLogger(__name__.rsplit('.')[-1])


class BaseCommand(ABC):
    _NAME = "BASECOMMAND"

    def __init__(self, plan_data):
        self._plan_data = plan_data

    @classmethod
    def get_name(cls) -> str:
        """Method returning a command name"""
        return cls._NAME

    @property
    def res_mngr(self) -> ResourceManager:
        return self._plan_data.access_resource_manager

    @property
    def plan_log(self) -> logging.Logger:
        return self._plan_data.plan_log

    @property
    def tsk_mngr(self) -> PlanTaskManagerProtocol:
        return self._plan_data.task_mngr

    @abstractmethod
    async def a_init(self):
        raise NotImplementedError

    @abstractmethod
    async def run(self):
        raise NotImplementedError
