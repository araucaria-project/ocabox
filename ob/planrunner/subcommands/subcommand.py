import logging
from ob.planrunner.base_command import BaseCommand


logger = logging.getLogger(__name__.rsplit('.')[-1])


class SubCommand(BaseCommand):

    def __init__(self, id: str, parent: 'Command', name: str, **kwargs) -> None:
        self.args = []
        self.kwargs = kwargs
        super().__init__(id=id, name=name, info_callback=parent.info_callback,
                         telescope=parent.telescope, c_type='subcommand', kwargs=self.kwargs)
        self._mk_folder(self.log_night_folder)
        self._create_command_string()

    def _create_command_string(self):
        kw = ''
        if len(self.args) > 0:
            for n in self.args:
                kw = f'{kw} {n}'
        w=0
        if len(self.kwargs) > 0:
            for n in self.kwargs.keys():
                if n != 'seq_data':
                    kw = f'{kw} {n}={self.kwargs[n]}'
                    w+=1
                #if w > 3: break
        self.info_callback['c_subcommands'](f'{self.id};{self.name};;{kw}')
        logger.debug(f'{self.id} is written')

    async def arun(self) -> int:
        raise NotImplementedError
