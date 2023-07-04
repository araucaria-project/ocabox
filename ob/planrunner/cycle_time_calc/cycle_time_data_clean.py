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

    def find_full_nights_id(self):
        random_id = ''
        line_started = None
        for n, m in enumerate(self.data_list):
            if m['command_name'] =='Night plan' and 'done' not in m.keys():
                random_id = m['random_id']
                line_started = n
            if m['command_name'] =='Night plan' and 'done' in m.keys() and random_id == m['random_id']:
                line_ended = n
                self.full_nights_id[random_id] = {'started': line_started,
                                                  'ended':line_ended,
                                                  'utc_time_stamp': m["utc_time_stamp"]}

    def build_commands_data(self):
        for n, m in self.full_nights_id.items():
            for p, q in enumerate(self.data_list):
                if m['started'] < p < m['ended']:
                    if q['command_name'] not in self.commands_data.keys():
                        self.commands_data[q['command_name']] = []
                    if 'done' not in q.keys() and self.data_list[p + 1]['skipped'] == 'False':
                        self.commands_data[q['command_name']].append(self._build_command_data(night_id=n, line_start=p))

    def verify_nights(self):
        f = self.read_file(folder=self.base_folder, file_name=self.night_verf_file_name)
        if f:
            l = f.split('\n')
            for n in l:
                if len(n) > 1:
                    d = self.decode_data(n)
                    if d['random_id'] in self.full_nights_id.keys():
                        if d['utc_time_stamp'] == self.full_nights_id[d['random_id']]['utc_time_stamp']:
                            self.full_nights_id.pop(d['random_id'])

    def save_commands_data_to_files(self):

        for n in self.commands_data.keys():
            for m in self.commands_data[n]:
                self.add_to_file(data=self.encode_data(m),
                                 folder=self.base_folder,
                                 file_name=self.clean_data_file_name(n))
        for p, q in self.full_nights_id.items():
            dat = OrderedDict({
                'random_id': p,
                'utc_time_stamp': q['utc_time_stamp'],
            })
            self.add_to_file(data=self.encode_data(data=dat),
                             folder=self.base_folder,
                             file_name=self.night_verf_file_name)

    def _build_command_data(self, night_id: str, line_start: int):
        first = self.data_list[line_start]
        second = self.data_list[line_start + 1]
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
            'rm_mode': CycleTimeDataClean.rm_mode(second),
            'dither': CycleTimeDataClean.dither(first),
            # 'dome_follow': '',
            # 'focus_distance': '',
            # 'mirror_cover_on': '',
            # 'focusing': '',

        })
        return dat

    def data_clean(self):
        """
        Method reading and cleaning only data from full nights (i.e. complete program) and only new data
        """
        self.parse_data()
        self.find_full_nights_id()
        self.verify_nights()
        self.build_commands_data()
        self.save_commands_data_to_files()


if __name__ == '__main__':
    c = CycleTimeDataClean('dev')
    c.data_clean()
