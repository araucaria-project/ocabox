from typing import Dict, Any
from .ctdata import CTData
from .abstract_cycle_time import AbstractCycleTime
import logging
from ocaboxapi.observatory import Observatory

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeDataClean(AbstractCycleTime):
    """
    This class represent cycle time data cleaner
    """

    def __init__(self):
        super().__init__()