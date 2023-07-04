from typing import Dict, Any


import logging


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeTrain:
    """
    This class represent cycle time trainer
    """

    def __init__(self):
        super().__init__()