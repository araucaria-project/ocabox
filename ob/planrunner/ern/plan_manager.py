import asyncio
import logging
from typing import Optional, Dict

from pyaraucaria.obs_plan.obs_plan_parser import ObsPlanParser

from ob.planrunner.ern.command import Command
from ob.planrunner.ern.plan_data import PlanData
from ob.planrunner.ern.plan_task_manager import PlanTaskManager

logger = logging.getLogger(__name__.rsplit('.')[-1])


class PlanManager:
    def __init__(self, loop: asyncio.AbstractEventLoop = None, **kwargs):
        super().__init__(**kwargs)
        self._loop = loop
        self._set_loop()
        self._plans: Dict[str, Command] = {}
        self._plan_runner_task = asyncio.Task = None
        self._running_plan_id: str = ""

    @staticmethod
    def _parse_plan(raw_plan: str):
        parser = ObsPlanParser()  # todo w przyszłości nie będzie instancji tego
        try:
            parsed_plan = parser.convert_from_string(raw_plan)
            logger.debug(f'Parsed: {parsed_plan}')
            return parsed_plan
        except asyncio.CancelledError:
            raise
        except Exception as e:  # todo powinny być konkretne błedy przechwytywane. Sprawdzić jakie
            logger.error(f"Unexpected error when parse plan: {e}")
        return None

    def upload_plan(self, plan_id: str, raw_plan: str, overwrite: bool = False) -> None:
        parsed_plan = self._parse_plan(raw_plan)
        if parsed_plan is None:
            logger.error(f'Plan is wrong. Check the syntax.')
            return
        if not overwrite and plan_id in self._plans:
            logger.warning(f"Plan with given id already exists.")
            return
        if self._running_plan_id == plan_id:
            logger.warning(f"Can not update plan witch id: {plan_id} because is actually running")
            return
        np = PlanManager.from_dict(parsed_plan, loop=self._loop)
        self._plans[plan_id] = np

    @classmethod
    def from_dict(cls, dic: dict, loop=None):
        # to jest metoda startowa każda klasa command będzie miała takąsamą u siebie w sierodku

        # ------------ część do usunięcia gdy parser zostanie poprawiony ------------
        dic = {"command_name": "SEQUENCE", "subcommands": dic[0].get("all_commands")}
        # ---------------------------------------------------------------------------
        # todo przerobić jakoś ten parser żeby zwracał standardowe klucze dla wszystkich poleciń. Dla SEQUENCE też:
        #  zamiast 'all_commands':[] to albo w argsach albo 'subcomands':[]
        task_mngr = PlanTaskManager()
        plans = Command.build_command(dic, PlanData(task_mngr=task_mngr), loop=loop)
        return plans

    def get_plan_structure(self, id_: str) -> Optional[Command]:
        try:
            return self._plans[id_]
        except LookupError:
            logger.info(f'There is no plan with id: {id_}')
        return None

    def delete_plan(self, id_: str) -> None:
        """
        Delete loaded plan from observation plan.

        :param id_: plan id (default: julian night date)
        """
        if self._running_plan_id == id_:
            logger.warning(f"Can not delete plan witch id: {id_} because is actually running")
            return
        if id_ in self._plans.keys():
            del self._plans[id_]
            logger.info(f"plan witch id: {id_} was successfully removed")

    async def run_plan(self, plan_id: str, step_id: str = None) -> None:
        if not self.is_stopped():
            logger.info(f"Can not run plan with id: {plan_id} because some plan is already running. "
                        f"It will have to be stopped first")
            return

        plan = self.get_plan_structure(plan_id)
        if plan is None:
            logger.info(f"Can not run plan with id: {plan_id}, Can not find it. it was not loaded")
            return

        self._running_plan_id = plan_id
        self._plan_runner_task = self._loop.create_task(self._main(plan=plan, step_id=step_id))

    def stop_plan(self) -> None:
        if not self.is_stopped() and not self._plan_runner_task.done():
            self._plan_runner_task.cancel()
            self._running_plan_id = ""

    def is_stopped(self):
        """
        Method return false if plan runer is actually running.

        :return: False if running
        """
        if self._plan_runner_task and self._plan_runner_task in asyncio.all_tasks(self._loop):
            return False
        return True

    def _set_loop(self):
        """

        :raise CommunicationRuntimeError:
        """
        if not self._loop:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error(f"{self}: Can not get current async loop, something goes wrong")
                raise  # todo dorobić błąd

    async def _main(self, plan, step_id):
        await plan.run()
        pass
