from typing import Dict, Any, List
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
import logging
from collections import OrderedDict
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
                    if 'done' not in q.keys():
                        self.commands_data[q['command_name']].append(self._build_command_data(line_start=p))

    def _build_command_data(self, line_start: int):
        if 'dome_az_end' in self.data_list[line_start + 2].keys():
            index_dome = 'dome_az_end'
        else:
            index_dome = 'dome_az_begin'
        if 'mount_alt_end' in self.data_list[line_start + 2].keys():
            index_mount_alt = 'mount_alt_end'
        else:
            index_mount_alt = 'mount_alt_begin'

        first = self.data_list[line_start]
        second = self.data_list[line_start + 1]
        third = self.data_list[line_start + 2]
        # TODO temember about 0,1
        dat = OrderedDict({
            'command_name': first['command_name'],
            'cycle_time': float(third['utc_time_stamp']) - float(first['utc_time_stamp']),
            'dome_az_distance': CycleTimeDataClean._dome_az_distance(start=float(first['dome_az_begin']),
                                                                     end=float(third[index_dome])),

            'mount_alt_distance': CycleTimeDataClean._mount_alt_az_distance(start_alt=1,
                                                                            end_alt=1,
                                                                            start_az=1,
                                                                            end_az=1)
        })
        return dat

    @staticmethod
    def _dome_az_distance(start: float, end: float) -> float:
        # TODO
        return start - end

    @staticmethod
    def _mount_alt_az_distance(start_alt: float, end_alt: float,  start_az: float, end_az: float) -> float:
        # TODO
        return 0


if __name__ == '__main__':
    c = CycleTimeDataClean('dev')
    c.parse_data()
    c.print_data_list()
    c.find_full_nights_id()
    c.build_commands_data()
    print(c.full_nights_id)
    print(c.commands_data)
