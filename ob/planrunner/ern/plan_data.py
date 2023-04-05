import dataclasses
import logging
import typing
import ob.planrunner.ern.command_Object
import ob.planrunner.ern.command_Sequence
from ob.data_colection.resource_manager.resource_manager import ResourceManager

logger = logging.getLogger(__name__.rsplit('.')[-1])


@dataclasses.dataclass
class PlanData:
    DEFAULT_MAP_COMMANDS: typing.ClassVar[dict] = {
        "SEQUENCE": ob.planrunner.ern.command_Sequence.CommandSequence,
        "OBJECT": ob.planrunner.ern.command_Object.CommandObject,
    }
    map_commands: dict = None
    resource_manager: ResourceManager = None
    _last_id: int = 0

    def __post_init__(self):
        if self.map_commands is None:
            self.map_commands = self.DEFAULT_MAP_COMMANDS

    def generate_next_id(self):
        self._last_id += 10
        return self._last_id
