from typing import Dict, Any
from .ctdata import CTData
import logging
from abc import ABC
import os
import datetime

logger = logging.getLogger(__name__.rsplit('.')[-1])


class AbstractCycleTime(ABC):
    """
    This class represent abstract time data
    """

    FILE_NAMES = {'raw_data': 'default.log', 'clean_data': 'cd'}


    def __init__(self, observatory: 'Observatory'):
        self.observatory = observatory
        super().__init__()

    @property
    def log_folder(self):
        if self.observatory:
            return os.path.expanduser(self.observatory.get_app_cfg('base_cycle_time_calc_dir',
                                                                   f'~/.oca/cycle_time_calc'))
        else:
            return os.path.expanduser(f'~/.oca/cycle_time_calc')

    def _mk_dirs(self):
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder, exist_ok=True)

    @staticmethod
    def to_log_file(data: str, folder: str, file_name: str) -> None:
        f = open(os.path.join(folder, file_name), "a")
        f.write(f'{data}')
        f.write('\n')
        f.close()

    @staticmethod
    def timestamp() -> datetime:
        return datetime.datetime.utcnow()