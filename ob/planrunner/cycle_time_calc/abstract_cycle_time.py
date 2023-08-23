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

    FILE_NAMES = {'raw_data': 'raw_data.txt', 'clean_data': 'clean_data.txt',
                  'night_verif': 'night_verif.txt', 'train_param': 'train_param.txt'}
    BASE_FOLDER_NAME = os.path.expanduser('~/.oca/cycle_time_calc')
    RM_MODES_MHZ = {"zb08": [5, 3, 1, 0.05],
                    "jk15": [1, 1, 1, 1, 1, 1, 1],
                    "wk06": [5, 3, 1, 0.05],
                    "dev": [1, 1, 1, 1, 1, 1, 1],
                    "sim": [1, 1, 1, 1, 1, 1, 1]}
    DATA_CLEAN_ORDER = ['night_id', 'command_name', 'start_utc_date_stamp', 'cycle_time', 'dome_distance',
                        'mount_distance', 'exposure_time_sum', 'filter_changes', 'rmmode_expno', 'dither_expno']
    X_COLUMNS = DATA_CLEAN_ORDER[4:]
    Y_COLUMN = DATA_CLEAN_ORDER[3]
    POSSIBLE_DITHER = ['OBJECT', 'SNAP']
    NO_TRAIN_COMMANDS = ['WAIT']

    @staticmethod
    def get_list_telesc(file_type: str) -> List[str]:
        l_dir = os.listdir(AbstractCycleTime.BASE_FOLDER_NAME)
        tel_lst = []
        for n in l_dir:
            if AbstractCycleTime.FILE_NAMES[file_type] in n:
                tel_lst.append(n.split('_')[0])
        return tel_lst

    @staticmethod
    def get_list_commands(telescope: str, file_type: str) -> List[str]:
        l_dir = os.listdir(AbstractCycleTime.BASE_FOLDER_NAME)
        com_lst = []
        for n in l_dir:
            if (AbstractCycleTime.FILE_NAMES[file_type] in n) and (telescope in n):
                com_lst.append(n.split('_')[1])
        return com_lst

    @staticmethod
    def encode_data(data: Dict or List) -> str:
        return json.dumps(data)

    @staticmethod
    def decode_data(data: str) -> Dict or List:
        return json.loads(data)

    @staticmethod
    def raw_file_name(telescope: str) -> str:
        return f'{telescope}_{AbstractCycleTime.FILE_NAMES["raw_data"]}'

    @staticmethod
    def night_verf_file_name(telescope: str)  -> str:
        return f'{telescope}_{AbstractCycleTime.FILE_NAMES["night_verif"]}'

    @staticmethod
    def clean_data_file_name(telescope: str , command: str) -> str:
        return f'{telescope}_{command}_{AbstractCycleTime.FILE_NAMES["clean_data"]}'

    @staticmethod
    def rm_modes_file_name() -> str:
        return f'{AbstractCycleTime.FILE_NAMES["rm_modes"]}'

    @staticmethod
    def train_param_file_name(telescope: str, command: str) -> str:
        return f'{telescope}_{command}_{AbstractCycleTime.FILE_NAMES["train_param"]}'

    @staticmethod
    def parse_data(data: str) -> List:
        ret = []
        s = data.split('\n')
        for n in s:
            if len(n) > 1:
                ret.append(AbstractCycleTime.decode_data(n))
        return ret

    @staticmethod
    def _mk_dirs() -> None:
        if not os.path.exists(AbstractCycleTime.BASE_FOLDER_NAME):
            os.makedirs(AbstractCycleTime.BASE_FOLDER_NAME, exist_ok=True)

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
    def time_stamp() -> datetime:
        return datetime.datetime.utcnow()

    @staticmethod
    def rm_mode(record: Dict[str, Any]) -> int:
        return int(record['readoutmode'])

    @staticmethod
    def rm_mode_inverse_mhz(rm_mode: int, telescope: str) -> float or int or None:
        dat = AbstractCycleTime.RM_MODES_MHZ
        if dat is not None:
            if telescope in dat.keys():
                if len(dat[telescope]) - 1 >= rm_mode:
                    try:
                        rm_mode_val = dat[telescope][rm_mode]
                        return 1/rm_mode_val
                    except IndexError:
                        logger.warning('Readoutmodes not match readoutmode - rm mode returned')
                        return rm_mode
                    except ZeroDivisionError:
                        logger.warning('Readoutmode value not right - rm mode returned')
                        return rm_mode
        else:
            logger.warning('Can not read readoutmode inverse MHz - rm mode returned')
            return rm_mode


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
        if np.array_equal(v1, v2):
            ret = 0.0
        else:
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
                    ret += int(n.split('/')[0])
        logger.debug(f'Record:{record}, seq_number:{ret}')
        return ret

    @staticmethod
    def last_filter(record: Dict[str, Any]) -> str:
        ret = 0
        if 'kwargs' in record.keys():
            if 'seq' in record['kwargs']:
                s = record['kwargs']['seq'].split(',')
                len_s = len(s)
                for w, n in enumerate(s, start=1):
                    if w == len(s):
                        z = n.split('/')
                        ret = z[1]
        logger.debug(f'Record:{record}, last filter is:{ret}')
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

    @staticmethod
    def dither_on(command_dict: Dict[str, Any]) -> int:
        """
        Do dithering or not.
        :return: bool
        """
        if 'kwargs' in command_dict.keys():
            kw = command_dict['kwargs']
        else:
            kw = {}
        if command_dict['command_name'] == 'SKYFLAT':
            if 'dither' not in kw.keys():
                return 1
            elif 'dither' in kw.keys() and kw['dither'] != 'none':
                return 1
            elif 'dither' in kw.keys() and kw['dither'] == 'none':
                return 0
            else:
                return 0

        elif command_dict['command_name'] in AbstractCycleTime.POSSIBLE_DITHER:
            if 'dither' not in kw.keys():
                return 0
            elif 'dither' in kw.keys() and kw['dither'] != 'none':
                return 1
            elif 'dither' in kw.keys() and kw['dither'] == 'none':
                return 0
            else:
                return 0
        else:
            return 1