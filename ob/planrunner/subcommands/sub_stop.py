from ob.planrunner.base_subcommand import BaseSubCommand
import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Stop(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',
                 info_callback: Dict[str, Callable], uobi: int, name: str = 'stop') -> None:
        super().__init__(id=id, info_callback=info_callback,
                         telescope=telescope,  name=name, uobi=uobi)
        self.create_sub_command_string()

    async def arun(self, step_id: str or None = None) -> int:
        logger.info(f'{self.id} started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        self.info_callback['stream_1'](f'{self.id} {self.name} started')
        self.done = True
        self.info_callback['stream_1'](f'{self.id} {self.name} done')
        self.info_callback['stream_5'](f'{self.id}')
        self.info_callback['exec_json'](self.exec_json())
        return 2
