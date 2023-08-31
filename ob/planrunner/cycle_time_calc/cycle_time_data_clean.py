from typing import Dict, Any, List
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
import logging
from collections import OrderedDict


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeDataClean(AbstractCycleTime):
    """
    This class represent cycle time data cleaner
    """

    @staticmethod
    def find_full_nights_id(data: List[Any]) -> Dict[str, Dict[str, Any]]:
        random_id = ''
        full_nights_id = {}
        line_started = None
        for n, m in enumerate(data, start=0):
            if m['command_name'] =='Night plan' and 'done' not in m.keys():
                random_id = m['random_id']
                line_started = n
            if m['command_name'] =='Night plan' and 'done' in m.keys() and random_id == m['random_id']:
                line_ended = n
                full_nights_id[random_id] = {'started': line_started,
                                             'ended':line_ended,
                                             'utc_time_stamp': m["utc_time_stamp"]}
        logger.debug(f'Full nights id find: {full_nights_id}')
        return full_nights_id

    @staticmethod
    def build_commands_data(data: List[Dict[str, Any]], telescope: str,
                            full_nights_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        commands_data = {}
        for n_id, m_dict in full_nights_id.items():
            for p_no, q_data in enumerate(data, start=0):
                if m_dict['started'] < p_no < m_dict['ended']:
                    if q_data['command_name'] not in commands_data.keys():
                        commands_data[q_data['command_name']] = []
                    if 'done' not in q_data.keys():
                        if data[p_no + 1]['skipped'] == 'False':
                            commands_data[q_data['command_name']].append(CycleTimeDataClean._build_command_data(
                                data=data,
                                telescope=telescope,
                                night_id=n_id,
                                line_start=p_no))
        return commands_data

    @staticmethod
    def verify_nights(full_nights_id: Dict[str, Dict[str, Any]], telescope: str):
        f = CycleTimeDataClean.read_file(folder=CycleTimeDataClean.BASE_FOLDER_NAME,
                                         file_name=CycleTimeDataClean.night_verif_file_name(telescope=telescope))
        if f is not None:
            l = f.split('\n')
            for n in l:
                if len(n) > 1:
                    d = CycleTimeDataClean.decode_data(n)
                    if d['random_id'] in full_nights_id.keys():
                        if d['utc_time_stamp'] == full_nights_id[d['random_id']]['utc_time_stamp']:
                            full_nights_id.pop(d['random_id'])
        else:
            pass
        return full_nights_id

    @staticmethod
    def save_commands_data_to_files(commands_data: Dict[str, Any],
                                    full_nights_id: Dict[str, Dict[str, Any]], telescope: str) -> None:
        logger.debug(f'Save commands data for telescope: {telescope}')
        for n in commands_data.keys():
            for m in commands_data[n]:
                CycleTimeDataClean.add_to_file(
                    data=CycleTimeDataClean.encode_data(m),
                    folder=CycleTimeDataClean.BASE_FOLDER_NAME,
                    file_name=CycleTimeDataClean.clean_data_file_name(telescope=telescope, command=n))
        for p, q in full_nights_id.items():
            dat = OrderedDict({
                'random_id': p,
                'utc_time_stamp': q['utc_time_stamp'],
            })
            CycleTimeDataClean.add_to_file(
                data=CycleTimeDataClean.encode_data(data=dat),
                folder=CycleTimeDataClean.BASE_FOLDER_NAME,
                file_name=CycleTimeDataClean.night_verif_file_name(telescope=telescope))

    @staticmethod
    def _build_command_data(data: List[Dict[str, Any]], telescope: str, night_id: str, line_start: int) -> Dict[str, Any]:
        first = data[line_start]
        second = data[line_start + 1]
        third = data[line_start + 2]

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

        dat = OrderedDict({
            CycleTimeDataClean.DATA_CLEAN_ORDER[0]:
                night_id,
            CycleTimeDataClean.DATA_CLEAN_ORDER[1]:
                first['command_name'],
            CycleTimeDataClean.DATA_CLEAN_ORDER[2]:
                first['utc_date_stamp'],
            CycleTimeDataClean.DATA_CLEAN_ORDER[3]:
                float(third['utc_time_stamp']) - float(first['utc_time_stamp']),
            CycleTimeDataClean.DATA_CLEAN_ORDER[4]:
                CycleTimeDataClean.az_distance(start=float(first['dome_az_begin']),
                                                                     end=float(third[index_dome])),
            CycleTimeDataClean.DATA_CLEAN_ORDER[5]:
                CycleTimeDataClean.alt_az_distance(start_alt=float(first['mount_alt_begin']),
                                                                     end_alt=float(third[index_mount_alt]),
                                                                     start_az=float(first['mount_az_begin']),
                                                                     end_az=float(third[index_mount_az])),
            CycleTimeDataClean.DATA_CLEAN_ORDER[6]:
                CycleTimeDataClean.exposure_time_sum(first),
            CycleTimeDataClean.DATA_CLEAN_ORDER[7]:
                CycleTimeDataClean.filter_changes(first),
            CycleTimeDataClean.DATA_CLEAN_ORDER[8]:
                CycleTimeDataClean.rm_mode_inverse_mhz(rm_mode=CycleTimeDataClean.rm_mode(second),
                                                       telescope=telescope)*CycleTimeDataClean.exposure_number(first),
            CycleTimeDataClean.DATA_CLEAN_ORDER[9]:
                CycleTimeDataClean.dither(first)*CycleTimeDataClean.exposure_number(first),
            # 'dome_follow': '',
            # 'focus_distance': '',
            # 'mirror_cover_on': '',
            # 'focusing': '',
        })
        return dat

    @staticmethod
    def data_clean(telescope: str) -> None:
        """
        Method reading and cleaning only data from full nights (i.e. complete program) and only new data
        """
        str_dat = CycleTimeDataClean.read_file(CycleTimeDataClean.BASE_FOLDER_NAME,
                                            CycleTimeDataClean.raw_file_name(telescope=telescope))
        parsed_data = CycleTimeDataClean.parse_data(str_dat)
        full_nights_id = CycleTimeDataClean.find_full_nights_id(parsed_data)
        full_nights_id = CycleTimeDataClean.verify_nights(full_nights_id=full_nights_id, telescope=telescope)
        commands_data = CycleTimeDataClean.build_commands_data(data=parsed_data,
                                                               telescope=telescope,
                                                               full_nights_id=full_nights_id)
        CycleTimeDataClean.save_commands_data_to_files(commands_data=commands_data,
                                                       full_nights_id=full_nights_id,
                                                       telescope=telescope)

    @staticmethod
    def data_clean_all() -> None:
        logger.debug(f'Data clean for all telescopes and all commands type')
        tel = CycleTimeDataClean.get_list_telesc(file_type='raw_data')
        for t in tel:
            logger.info(f'Data clean for telescope: {t}')
            CycleTimeDataClean.data_clean(telescope=t)
