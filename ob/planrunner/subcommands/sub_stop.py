from ob.planrunner.subcommand import SubCommand
import logging


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Stop(SubCommand):

    def __init__(self, id: str, parent: 'Command', name: str = 'stop', **kwargs) -> None:
        self.telescope = parent.telescope
        self.kwargs = kwargs
        super().__init__(id=id, parent=parent, name=name, **kwargs)

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