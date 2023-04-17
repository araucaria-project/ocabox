import asyncio
import logging
from typing import List
from ob.planrunner.ern.command import Command
from ob.planrunner.ern.command_error import CriticalCommandError, NormalCommandError

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CommandSequence(Command):
    _NAME = "SEQUENCE"
    # --- arg keys ---
    _SUBCOMMANDS_KEY = "subcommands"

    def __init__(self, command_dict: dict, plan_data, previous_command, id_: str = None,
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

    async def _run_body(self):
        await self._wait_for_previous_command_finish()
        self.log("Start doing")
        tasks = []
        for s in self.get_subcommands():
            self.log(f"Waiting for free task slot")
            t = await self.tsk_mngr.run_task_when_can(s.run(), is_independent=True)
            self.log(f"Created task for {s.get_name()} Id: {s.get_id()}")
            tasks.append(t)
        
        # result = await asyncio.gather(*tasks)
        for t in tasks:
            try:
                await t
            except asyncio.CancelledError:
                self.log("Task was canceled - Stop the rest of the tasks in this sequence", lvl=logging.ERROR)
                await self._cancel_tasks(tasks)
                break
            except CriticalCommandError:
                self.log("Task has CRITICAL error - Stop the rest of the tasks in this sequence", lvl=logging.ERROR)
                await self._cancel_tasks(tasks)
                break
            except NormalCommandError:
                self.log("Task has normal error - ignore and continue with the rest of the commands",
                         lvl=logging.WARNING)
            except Exception as e:
                self.log(f"Task has unexpected error: {e} - Stop the rest of the tasks in this sequence",
                         lvl=logging.ERROR)
                await self._cancel_tasks(tasks)
                break
        self.log("All subcommand finished")

    @staticmethod
    async def _cancel_tasks(tasks):
        for t in tasks:
            t.cancel()
            # await asyncio.gather(*tasks, return_exceptions=True)
