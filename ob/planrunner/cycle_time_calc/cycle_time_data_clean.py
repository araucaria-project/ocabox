from typing import Dict, Any, List
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
import logging
from collections import OrderedDict
import math
import numpy as np


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeDataClean(AbstractCycleTime):
    """
    This class represent cycle time data cleaner
    """

    def __init__(self, telescope_name: str):
        self.full_nights_id: Dict[str, Dict[str, int]] = {}
        self.commands_data: Dict[str, List[Dict[str, Any]]] = {}
        super().__init__(telescope_name=telescope_name)

    def read_data_from_file(self):
        self._data = self.read_file(self.base_folder, self.raw_file_name)

    def print_data_list(self):
        for n in self.data_list:
            print(n)

    def find_full_nights_id(self):
        random_id = ''
        line_started = None
        for n, m in enumerate(self.data_list):
            if m['command_name'] =='Night plan' and 'done' not in m.keys():
                random_id = m['random_id']
                line_started = n
            if m['command_name'] =='Night plan' and 'done' in m.keys() and random_id == m['random_id']:
                line_ended = n
                self.full_nights_id[random_id] = {'started': line_started, 'ended':line_ended}

    def build_commands_data(self):
        for n, m in self.full_nights_id.items():
            for p, q in enumerate(self.data_list):
                if m['started'] < p < m['ended']:
                    if q['command_name'] not in self.commands_data.keys():
                        self.commands_data[q['command_name']] = []
                    if 'done' not in q.keys() and self.data_list[p + 1]['skipped'] == 'False':
                        self.commands_data[q['command_name']].append(self._build_command_data(night_id=n, line_start=p))

    def _build_command_data(self, night_id: str, line_start: int):
        first = self.data_list[line_start]
        # second = self.data_list[line_start + 1]
        third = self.data_list[line_start + 2]

        if 'dome_az_end' in third.keys():
            index_dome = 'dome_az_end'
        else:
            index_dome = 'dome_az_begin'

        if 'mount_alt_end' in third.keys():
            index_mount_alt = 'mount_alt_end'
        else:
            index_mount_alt = 'mount_alt_begin'

        if 'mount_az_end' in third.keys():
            index_mount_az = 'mount_az_end'
        else:
            index_mount_az = 'mount_az_begin'


        # TODO remember about 0,1
        dat = OrderedDict({
            'night_id': night_id,
            'command_name': first['command_name'],
            'start_utc_date_stamp': first['utc_date_stamp'],
            'cycle_time': float(third['utc_time_stamp']) - float(first['utc_time_stamp']),
            'dome_distance': CycleTimeDataClean.az_distance(start=float(first['dome_az_begin']),
                                                                     end=float(third[index_dome])),
            'mount_distance': CycleTimeDataClean.alt_az_distance(start_alt=float(first['mount_alt_begin']),
                                                                     end_alt=float(third[index_mount_alt]),
                                                                     start_az=float(first['mount_az_begin']),
                                                                     end_az=float(third[index_mount_az])),
            'exposure_time_sum': CycleTimeDataClean.exposure_time_sum(first),
            'seq_number': CycleTimeDataClean.seq_number(first),
            'filter_changes': CycleTimeDataClean.filter_changes(first),
            #'mirror_cover_on': '',
            'focus_distance': '',
            'dome_follow': '',
            'dither': CycleTimeDataClean.dither(first),


        })
        return dat

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
        return ret

    @staticmethod
    def vector(alt: float, az: float) -> np.array:
        """

        :param alt: alt degrees
        :param az: az degrees
        :return: numpy vector
        """
        az = math.radians(az)
        alt = math.radians(alt)
        x = math.cos(az) * math.cos(alt)
        z = math.sin(az) * math.cos(alt)
        y = math.sin(alt)
        return np.array([x, y, z])

    @staticmethod
    def alt_az_distance(start_alt: float, end_alt: float,  start_az: float, end_az: float) -> float:
        """
        Method calculate angle between altaz positions
        :param start_alt: start alt degrees
        :param end_alt: end alt degrees
        :param start_az: start az degrees
        :param end_az: end az degrees
        :return: distance in degrees
        """
        v1 = CycleTimeDataClean.vector(alt=start_alt, az=start_az)
        v2 = CycleTimeDataClean.vector(alt=end_alt, az=end_az)
        return math.degrees(math.acos(np.dot(v1, v2)))

    @staticmethod
    def exposure_time_sum(record: Dict[str, Any]) -> float:
        ret = 0
        if 'kwargs' in record.keys():
            if 'seq' in record['kwargs']:
                s = record['kwargs']['seq'].split(',')
                for n in s:
                    z = n.split('/')
                    ret += int(z[0])*float(z[2])
        return ret

    @staticmethod
    def seq_number(record: Dict[str, Any]) -> int:
        ret = 0
        if 'kwargs' in record.keys():
            if 'seq' in record['kwargs']:
                s = record['kwargs']['seq'].split(',')
                for n in s:
                    ret += 1
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
        return ret


if __name__ == '__main__':
    c = CycleTimeDataClean('dev')
    c.parse_data()
    c.print_data_list()
    c.find_full_nights_id()
    c.build_commands_data()
    print(c.full_nights_id)
    print(c.commands_data)
