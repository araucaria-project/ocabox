import logging
from abc import ABC, abstractmethod
import os
from typing import Dict, Any, List
import json
import datetime
logger = logging.getLogger(__name__.rsplit('.')[-1])
#from ocaboxapi.observatory import Observatory

class AbstractCycleTime(ABC):
    """
    This class represent abstract time data
    """

    FILE_NAMES = {'raw_data': 'raw_data.txt', 'clean_data': 'clean_data.txt'}
    BASE_FOLDER_NAME = os.path.expanduser('~/.oca/cycle_time_calc')


    def __init__(self, telescope_name: str):
        self.telescope_name = telescope_name
        self._data: str = ''
        self.data_list: List[Dict[str, str]] = []
        self._mk_dirs()
        super().__init__()

    @property
    def raw_file_name(self, ) -> str:
        return f'{self.telescope_name}_{self.FILE_NAMES["raw_data"]}'

    @property
    def clean_data_file_name(self, ) -> str:
        return f'{self.telescope_name}_{self.FILE_NAMES["clean_data"]}'

    @abstractmethod
    def read_data_from_file(self):
        raise NotImplementedError

    def parse_data(self):
        self.read_data_from_file()
        self._data = self._data.replace("'", '"')
        s = self._data.split('\n')
        for n in s:
            if len(n) > 1:
                self.data_list.append(json.loads(n))

    @property
    def base_folder(self):
        return self.BASE_FOLDER_NAME

    def _mk_dirs(self):
        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder, exist_ok=True)

    @staticmethod
    def add_to_file(data: str, folder: str, file_name: str) -> None:
        f = open(os.path.join(folder, file_name), "a", encoding='utf-8')
        f.write(f'{data}')
        f.write('\n')
        f.close()

    @staticmethod
    def read_file(folder: str, file_name: str) -> str:
        try:
            f = open(os.path.join(folder, file_name), "r", encoding='utf-8')
            dat = f.read()
            f.close()
            return dat
        except FileExistsError:
            logger.error(f'File {file_name} do not exists')

    @staticmethod
    def timestamp() -> datetime:
        return datetime.datetime.utcnow()