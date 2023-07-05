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

    def read_data_from_file(self, command: str or None = None):
        self._data = self.read_file(self.base_folder, self.raw_file_name)

    def find_full_nights_id(self):
        random_id = ''
        line_started = None
        for n, m in enumerate(self.data_list, start=0):
            if m['command_name'] =='Night plan' and 'done' not in m.keys():
                random_id = m['random_id']
                line_started = n
            if m['command_name'] =='Night plan' and 'done' in m.keys() and random_id == m['random_id']:
                line_ended = n
                self.full_nights_id[random_id] = {'started': line_started,
                                                  'ended':line_ended,
                                                  'utc_time_stamp': m["utc_time_stamp"]}

    def build_commands_data(self):
        for n_id, m_dict in self.full_nights_id.items():
            print(self.full_nights_id)
            for p_no, q_data in enumerate(self.data_list):
                if m_dict['started'] < p_no < m_dict['ended']:
                    if q_data['command_name'] not in self.commands_data.keys():
                        self.commands_data[q_data['command_name']] = []
                    if 'done' not in q_data.keys():
                        if self.data_list[p_no + 1]['skipped'] == 'False':
                            self.commands_data[q_data['command_name']].append(self._build_command_data(night_id=n_id,
                                                                                                       line_start=p_no))

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
        print(self.data_list[line_start], line_start)
        second = self.data_list[line_start + 1]
        print(self.data_list[line_start + 1], line_start + 1)
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
            self.DATA_CLEAN_ORDER[0]: night_id,
            self.DATA_CLEAN_ORDER[1]: first['command_name'],
            self.DATA_CLEAN_ORDER[2]: first['utc_date_stamp'],
            self.DATA_CLEAN_ORDER[3]: float(third['utc_time_stamp']) - float(first['utc_time_stamp']),
            self.DATA_CLEAN_ORDER[4]: CycleTimeDataClean.az_distance(start=float(first['dome_az_begin']),
                                                                     end=float(third[index_dome])),
            self.DATA_CLEAN_ORDER[5]: CycleTimeDataClean.alt_az_distance(start_alt=float(first['mount_alt_begin']),
                                                                     end_alt=float(third[index_mount_alt]),
                                                                     start_az=float(first['mount_az_begin']),
                                                                     end_az=float(third[index_mount_az])),
            self.DATA_CLEAN_ORDER[6]: CycleTimeDataClean.exposure_time_sum(first),
            self.DATA_CLEAN_ORDER[7]: CycleTimeDataClean.filter_changes(first),
            self.DATA_CLEAN_ORDER[8]: CycleTimeDataClean.rm_mode(second)*CycleTimeDataClean.exposure_number(first),
            self.DATA_CLEAN_ORDER[9]: CycleTimeDataClean.dither(first)*CycleTimeDataClean.exposure_number(first),
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
        self.read_data_from_file()
        self.parse_data()
        self.find_full_nights_id()
        self.verify_nights()
        self.build_commands_data()
        print(self.commands_data)
        self.save_commands_data_to_files()
        # remove raw data ?


if __name__ == '__main__':
    c = CycleTimeDataClean('dev')
    c.data_clean()
