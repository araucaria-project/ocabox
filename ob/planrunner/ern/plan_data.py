import dataclasses
import logging
import typing
import ob.planrunner.ern.commands.command_Object
import ob.planrunner.ern.commands.command_Sequence
from ob.comunication.internal_client_api import InternalClientAPI
from ob.data_colection.resource_manager.resource_manager import TelescopeComponentManager
from ob.planrunner.ern.commands.commands_names import CommandsNames
from ob.planrunner.ern.plan_task_manager import PlanTaskManager
from ob.planrunner.ern.plan_task_manager_protocol import PlanTaskManagerProtocol
from ob.planrunner.plan_status_publisher import PlanStatusPublisher

logger = logging.getLogger(__name__.rsplit('.')[-1])


@dataclasses.dataclass
class PlanData:

    access_resource_manager: TelescopeComponentManager
    client_api: InternalClientAPI
    DEFAULT_MAP_COMMANDS: typing.ClassVar[dict] = {
        CommandsNames.SEQUENCE: ob.planrunner.ern.commands.command_Sequence.CommandSequence,
        CommandsNames.OBJECT: ob.planrunner.ern.commands.command_Object.CommandObject,
    }
    task_mngr: PlanTaskManagerProtocol = None
    status_pub: PlanStatusPublisher = None
    plan_log: logging.Logger = logging.getLogger(name="ObsPlanLog")
    map_commands: dict = None
    _last_id: int = 0

    def __post_init__(self):
        if self.task_mngr is None:
            self.task_mngr = PlanTaskManager()
        if self.map_commands is None:
            self.map_commands = self.DEFAULT_MAP_COMMANDS
        if self.status_pub is None:
            self.status_pub = PlanStatusPublisher()

    def generate_next_id(self) -> str:
        self._last_id += 10
        return str(self._last_id)
