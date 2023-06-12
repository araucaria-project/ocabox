from ob.planrunner.subcommand import SubCommand
import logging


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Stop(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'stop', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.kwargs = kwargs
        self.id = id
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def arun(self, step_id: str or None = None) -> int:
        logger.info(f'{self.id} started')
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} started')
        self.done = True
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        self.info_callback['exec_json'](self.exec_json())
        return 2