import logging
from abc import ABC, abstractmethod
import os
from typing import Dict, Any, List
import datetime
import math
import numpy as np
import json


logger = logging.getLogger(__name__.rsplit('.')[-1])


class AbstractCycleTime(ABC):
    """
    This class represent abstract time data
    """

    FILE_NAMES = {'raw_data': 'raw_data.txt', 'clean_data': 'clean_data.txt', 'night_verif': 'night_verif.txt'}
    BASE_FOLDER_NAME = os.path.expanduser('~/.oca/cycle_time_calc')
    DATA_CLEAN_ORDER = ['night_id', 'command_name', 'start_utc_date_stamp', 'cycle_time', 'dome_distance',
                        'mount_distance', 'exposure_time_sum', 'filter_changes', 'rmmode_expno', 'dither_expno']


    def __init__(self, telescope_name: str):
        self.telescope_name = telescope_name
        self._data: str = ''
        self.data_list: List[Dict[str, str]] = []

        self._mk_dirs()
        super().__init__()

    @staticmethod
    def encode_data(data: Dict or List) -> str:
        return json.dumps(data)

    @staticmethod
    def decode_data(data: str) -> Dict or List:
        return json.loads(data)

    @property
    def raw_file_name(self) -> str:
        return f'{self.telescope_name}_{self.FILE_NAMES["raw_data"]}'

    @property
    def night_verf_file_name(self) -> str:
        return f'{self.telescope_name}_{self.FILE_NAMES["night_verif"]}'

    def clean_data_file_name(self, command: str) -> str:
        return f'{self.telescope_name}_{command}_{self.FILE_NAMES["clean_data"]}'

    @abstractmethod
    def read_data_from_file(self, command: str or None = None):
        raise NotImplementedError

    def parse_data(self):
        s = self._data.split('\n')
        for n in s:
            if len(n) > 1:
                self.data_list.append(self.decode_data(n))

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
    def read_file(folder: str, file_name: str) -> str or None:
        try:
            f = open(os.path.join(folder, file_name), "r", encoding='utf-8')
            dat = f.read()
            f.close()
            logger.debug(f'File read')
            return dat
        except (FileExistsError, FileNotFoundError):
            logger.error(f'File {file_name} do not exists')
            return None

    @staticmethod
    def timestamp() -> datetime:
        return datetime.datetime.utcnow()

    @staticmethod
    def rm_mode(record: Dict[str, Any]) -> int:
        # TODO rethink this
        return int(record['readoutmode']) + 1

    @staticmethod
    def dither(record: Dict[str, Any]) -> int:
        if record['dither'] == 'True':
            return 1
        else:
            return 0

    @staticmethod
    def az_distance(start: float, end: float) -> float:
        """
        Method giving back shortest distance in azimuth
        :param start: start position of azimuth
        :param end: end position of azimuth
        :return: shortest distance in degrees
        """
        if abs(start - end) > 180.0:
            if start > end:
                ret = abs(start - (end + 360.0))
            else:
                ret = abs(end - (start + 360.0))
        else:
            ret = abs(start - end)
        logger.debug(f'Az_start:{start}, az_end:{end}, az_distance:{ret}')
        return ret

    @staticmethod
    def vector(alt: float, az: float) -> np.array:
        """
        Method builds vector from alt az
        :param alt: alt degrees
        :param az: az degrees
        :return: numpy vector
        """
        az = math.radians(az)
        alt = math.radians(alt)
        x = math.cos(az) * math.cos(alt)
        z = math.sin(az) * math.cos(alt)
        y = math.sin(alt)
        ret = np.array([x, y, z])
        logger.debug(f'Alt:{alt}, az:{az}, vector:{ret}')
        return ret

    @staticmethod
    def alt_az_distance(start_alt: float, end_alt: float, start_az: float, end_az: float) -> float:
        """
        Method calculate angle between altaz positions
        :param start_alt: start alt degrees
        :param end_alt: end alt degrees
        :param start_az: start az degrees
        :param end_az: end az degrees
        :return: distance in degrees
        """
        v1 = AbstractCycleTime.vector(alt=start_alt, az=start_az)
        v2 = AbstractCycleTime.vector(alt=end_alt, az=end_az)
        ret = math.degrees(math.acos(np.dot(v1, v2)))
        logger.debug(f'Alt_start:{start_alt}, alt_end:{end_alt}, az_start:{start_az},'
                     f' az_end:{end_az}, altaz_distance:{ret}')
        return ret

    @staticmethod
    def exposure_time_sum(record: Dict[str, Any]) -> float:
        ret = 0
        if 'kwargs' in record.keys():
            if 'seq' in record['kwargs']:
                s = record['kwargs']['seq'].split(',')
                for n in s:
                    z = n.split('/')
                    ret += int(z[0]) * float(z[2])
        logger.debug(f'Record:{record}, exposure_time_sum:{ret}')
        return ret

    @staticmethod
    def seq_number(record: Dict[str, Any]) -> int:
        ret = 0
        if 'kwargs' in record.keys():
            if 'seq' in record['kwargs']:
                s = record['kwargs']['seq'].split(',')
                for n in s:
                    ret += 1
        logger.debug(f'Record:{record}, seq_number:{ret}')
        return ret

    @staticmethod
    def exposure_number(record: Dict[str, Any]) -> int:
        ret = 0
        if 'kwargs' in record.keys():
            if 'seq' in record['kwargs']:
                s = record['kwargs']['seq'].split(',')
                for n in s:
                    ret += int(n[0])
        logger.debug(f'Record:{record}, seq_number:{ret}')
        return ret

    @staticmethod
    def filter_changes(record: Dict[str, Any]) -> int:
        ret = 0
        f = record['filter_pos']
        if 'kwargs' in record.keys():
            if 'seq' in record['kwargs']:
                s = record['kwargs']['seq'].split(',')
                for n in s:
                    z = n.split('/')
                    if f != z[1]:
                        ret += 1
                    f = z[1]
        logger.debug(f'Record:{record}, filter_changes:{ret}')
        return ret