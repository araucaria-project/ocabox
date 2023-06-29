from typing import Dict, Any
from ob.planrunner.cycle_time_calc.ctdata import CTData
import logging


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeDataClean:
    """
    This class represent cycle time data cleaner
    """

    def __init__(self):
        super().__init__()