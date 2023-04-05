import asyncio
import logging
from typing import List, Any, Optional

from pyaraucaria.obs_plan.obs_plan_parser import ObsPlanParser

from ob.planrunner.ern.command import Command
# from ob.planrunner.ern.command_Object import CommandObject
# from ob.planrunner.ern.command_Sequence import CommandSequence
from ob.planrunner.ern.plan_data import PlanData

logger = logging.getLogger(__name__.rsplit('.')[-1])


class PlanManager:
    def __init__(self):
        super().__init__()
        self.parsed_plan: List[Any] = []
        self.raw_plan: Optional[str] = None
        self._obs_structure = None
        self._plans = {}

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

    def load_plan(self, plan_id: str, raw_plan: str, overwrite: bool = False) -> None:
        self.raw_plan = raw_plan
        parsed_plan = self._parse_plan(raw_plan)
        self.parsed_plan = parsed_plan
        if parsed_plan is not None:
            try:
                # np = NightPlan(nightplan_id, nightplan_dict, self)
                np = PlanManager.from_dict(parsed_plan)
                self._plans[plan_id] = np
            except CantOverideNightPlanError:
                logger.error(f'Cannot overwrite nightplan {plan_id}, please select overwrite=True')
        else:
            logger.error(f'Plan is wrong. Check the syntax.')

    @classmethod
    def from_dict(cls, dic: dict, loop):
        # to jest metoda startowa każda klasa command będzie miała takąsamą u siebie w sierodku

        # ------------ część do usunięcia gdy parser zostanie poprawiony ------------
        dic = {"command_name": "SEQUENCE", "subcommands": dic[0].get("all_commands")}
        # ---------------------------------------------------------------------------
        print(dic)
        # todo przerobić jakoś ten parser żeby zwracał standardowe klucze dla wszystkich poleciń. Dla SEQUENCE też:
        #  zamiast 'all_commands':[] to albo w argsach albo 'subcomands':[]
        plans = Command.build_command(dic, PlanData(), loop=loop)
        return plans


class CantOverideNightPlanError(Exception):
    pass


class SequenceTreeError(Exception):
    pass
