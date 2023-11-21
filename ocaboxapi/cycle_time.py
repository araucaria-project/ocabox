import logging
from ob.planrunner.cycle_time_calc.cycle_time_calc import  CycleTimeCalc
from ob.planrunner.cycle_time_calc.cycle_time_data_clean import CycleTimeDataClean
from ob.planrunner.cycle_time_calc.cycle_time_train import CycleTimeTrain

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTime(CycleTimeCalc):

    def __init__(self, telescope: 'Telescope') -> None:
        super().__init__(telescope=telescope)

    def clean_and_train_on_exit(self):
        CycleTimeDataClean.data_clean_all()
        CycleTimeTrain.train_all_telesc_all_commands()
