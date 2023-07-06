from typing import Dict, Any, List
import logging
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeCalc(AbstractCycleTime):
    """
    This class represent cycle time calculator
    """

    def __init__(self, telescope: str):
        self.available_param: Dict[str, Dict[str, Any]] = {}
        self._complete_time: float = 0.0
        self._rmode: int = 0
        self._alt_mount: float = 0.0
        self._az_mount: float = 0.0
        self._az_dome: float = 0.0
        self.telescope = telescope
        super().__init__()
        self._get_params()

    @property
    def avialable_param_telesc(self) -> Dict[str, Any] or None:
        if self.telescope in self.available_param.keys():
            return self.available_param[self.telescope]
        else:
            return None

    @property
    def avialable_param_telesc_commands(self) -> List[str]:
        li = []
        for ke, val in self.avialable_param_telesc.items():
            li.append(ke)
        return li

    def _get_params(self):
        for t in CycleTimeCalc.get_list_telesc(file_type='train_param'):
            self.available_param[t] = {}
            for c in CycleTimeCalc.get_list_commands(telescope=t, file_type='train_param'):
                data = CycleTimeCalc.get_last_param(telescope=t, command=c)
                self.available_param[t][c] = data

    @staticmethod
    def get_last_param(telescope: str, command: str):
        data = CycleTimeCalc.read_file(CycleTimeCalc.BASE_FOLDER_NAME,
                                        CycleTimeCalc.train_param_file_name(telescope=telescope, command=command))
        return CycleTimeCalc.parse_data(data=data)[-1]

    def set_start_rmode(self, rmode):
        self._rmode = rmode

    #TODO change _rmode along operations


    z = ['command_name''dome_distance','mount_distance', 'exposure_time_sum',
         'filter_changes', 'rmmode_expno', 'dither_expno']

    u = {"night_id": "326777", "command_name": "OBJECT", "start_utc_date_stamp": "2023-07-05T13:33:56.870223",
     "cycle_time": 25.262605905532837, "dome_distance": 0.0, "mount_distance": 0.10341941737077996,
     "exposure_time_sum": 15.0, "filter_changes": 2, "rmmode_expno": 7, "dither_expno": 0}

    # TODO get first rm from telescope
    # TODO rest read from data

    const = ['rmode', ]
    """
    ['command_name'],


    CycleTimeDataClean.DATA_CLEAN_ORDER[1]:
    first['command_name'],"""


    """
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
    CycleTimeDataClean.rm_mode(second) * CycleTimeDataClean.exposure_number(first),
    CycleTimeDataClean.DATA_CLEAN_ORDER[9]:
    CycleTimeDataClean.dither(first) * CycleTimeDataClean.exposure_number(first),"""


    def calc_time(self, command_str: Dict[str, Any]) -> float or None:

        if command_str['command_name'] in self.avialable_param_telesc_commands:
            time = 0


            return time
        else:
            logger.debug(f'Cannot calculate time, lack of params')
            return None

if __name__ == '__main__':
    c = CycleTimeCalc('dev')
    print(c.avialable_param_telesc)
    print(c.avialable_param_telesc_commands)