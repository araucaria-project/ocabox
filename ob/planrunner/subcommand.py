import logging

logger = logging.getLogger(__name__.rsplit('.')[-1])


class SubCommand:

    def __init__(self, id: str, parent: 'Command', subcommand_name: str or None = None, **kwargs) -> None:
        self.id = id
        self.args = []
        self.kwargs = kwargs
        self.subcommand_name = subcommand_name
        self.info_callback = parent.info_callback
        super().__init__()
        self._create_command_string()

    async def arun(self) -> None:
        raise NotImplementedError

    def _create_command_string(self):
        kw = ''
        for n in self.args:
            kw = f'{kw} {n}'
        for n in self.kwargs.keys():
            kw = f'{kw} {n}={self.kwargs[n]}'
        self.info_callback['c_subcommands'](f'{self.id} {self.subcommand_name}{kw}')
        logger.info(f'Subcommand {self.id} name: {self.subcommand_name} is written')