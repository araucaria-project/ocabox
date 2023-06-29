from typing import Dict, Any
from ob.planrunner.cycle_time_calc.ctdata import CTData
import logging


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeCalc:
    """
    This class represent cycle time calculator
    """

    def __init__(self):
        super().__init__()