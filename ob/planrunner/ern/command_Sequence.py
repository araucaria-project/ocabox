import asyncio
import logging
from typing import List
from ob.planrunner.ern.command import Command

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CommandSequence(Command):
    _NAME = "SEQUENCE"
    _SUBCOMMANDS_KEY = "subcommands"

    def __init__(self, command_dict: dict, plan_data, id_: str = None, previous_command=None,
                 loop: asyncio.AbstractEventLoop = None, **kwargs):
        super().__init__(command_dict=command_dict, plan_data=plan_data, id_=id_, previous_command=previous_command,
                         loop=loop, **kwargs)
        self._subcommands: List[Command] = []
        self._create_subcommands_objects(self._command_dict.get(self._SUBCOMMANDS_KEY, []))

    def _create_subcommands_objects(self, subcommands: list):
        if not subcommands:
            logger.info(f"Command {self._NAME} has empty list of Subcommands")
            return
        if not isinstance(subcommands, list):
            logger.error(f"Command {self._NAME} get subcommands type {type(subcommands)} instead {list}. "
                         f"Subcommand will be not created")
            return
        com = None
        for s in subcommands:
            com = Command.build_command(dic=s, plan_data=self._plan_data, previous_command=com, loop=self._loop)
            self._subcommands.append(com)

    def get_subcommands(self) -> List[Command]:
        return self._subcommands

    # todo ostatni z sekwencji musi ustawić flage zakończenia na sekwencji - dorobić taki pechamizm gdzieś potem

    async def run(self):
        await self.a_init()
        if self._loop is None:
            # todo  ustawić status na skończony
            return
        tasks = []
        for s in self.get_subcommands():
            t = self.tsk_mngr.run_task_when_can(s.run(), is_independent=True)
            tasks.append(t)

        await asyncio.gather(*tasks)
        self._finish_locking.set_result(True)
        self._finish.set_result(True)

