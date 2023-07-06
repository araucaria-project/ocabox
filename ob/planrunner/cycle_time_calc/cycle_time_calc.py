from typing import Dict, Any, List
import logging
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
import datetime
from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeCalc(AbstractCycleTime):
    """
    This class represent cycle time calculator
    """

    def __init__(self, telescope: str):
        self.available_param: Dict[str, Dict[str, Any]] = {}
        self._rmode: int = 0
        self._current_filter: str = ''
        self._alt_mount: float = 70.0
        self._az_mount: float = 0.0
        self._az_dome: float = 0.0
        self.telescope = telescope
        self._time_length: float = 0.0
        self._start_time: datetime.datetime or None = None
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

    def set_start_time(self, utc_time_stamp: datetime.datetime or None = None):
        if utc_time_stamp is None:
            self._start_time = CycleTimeCalc.time_stamp().timestamp()
        else:
            self._start_time = utc_time_stamp

    def set_telescope_start_az_alt(self, az: float, alt: float):
        self._alt_mount = alt
        self._az_mount = az

    def set_dome_start_az(self, az: float):
        self._az_dome = az

    # TODO get first rm from telescope
    # TODO rest read from data
    # TODO mount distance calculate from ra, dec (no matter if ra dec or altaz - calculate same)
    # TODO dome distance calculate from ra change?

    def _mount_altaz_target(self, command_dict: Dict[str, Any]) -> Dict[str, float] or None:
        altaz = None
        if 'args' in command_dict.keys():
            if len(command_dict['args']) == 2:
                ra = command_dict['args'][0]
                dec = command_dict['args'][1]
            elif len(command_dict['args']) == 3:
                ra = command_dict['args'][1]
                dec = command_dict['args'][2]
            else:
                ra = None
                dec = None
            if (self._start_time is None) and (ra is not None) and (dec is not None):
                altaz = {'az': ra_to_decimal(ra), 'alt': dec_to_decimal(dec)}
            else:
                # ++++++TODO DO START TIME FOR CALC AND EVENTUALLY SKIPPING OPERATIONS ZERO TIME++++++
                pass
        else:
            pass
        if 'kwargs' in command_dict.keys():
            if ('az' and 'alt') in command_dict['kwargs'].keys():
                az = float(command_dict['kwargs']['az'])
                alt = float(command_dict['kwargs']['alt'])
                altaz = {'az': az, 'alt': alt}
        return altaz


    def calc_time(self, command_dict: Dict[str, Any]) -> float or None:

        if command_dict['command_name'] in self.avialable_param_telesc_commands:
            azalt = self._mount_altaz_target(command_dict=command_dict)
            if azalt is not None:
                mount_alt_az_dist = CycleTimeCalc.alt_az_distance(start_alt=self._alt_mount,
                                                                  end_alt=azalt['alt'],
                                                                  start_az=self._az_mount,
                                                                  end_az=azalt['az'])
                dome_az_dist = CycleTimeCalc.az_distance(start=self._az_dome, end=azalt['az'])
            else:
                mount_alt_az_dist = 0.0
                dome_az_dist = 0.0
            command_dict_param = {}
            exp_no = CycleTimeCalc.exposure_number(command_dict)
            dither = CycleTimeCalc.dither_on(command_dict=command_dict)
            command_dict['filter_pos'] = self._current_filter
            command_dict_param['dome_distance'] = dome_az_dist
            command_dict_param['mount_distance'] = mount_alt_az_dist
            command_dict_param['exposure_time_sum'] = CycleTimeCalc.exposure_time_sum(command_dict)
            command_dict_param['filter_changes'] = CycleTimeCalc.filter_changes(command_dict)
            # TODO make func to leave filter on right position
            command_dict_param['rmmode_expno'] = (self._rmode + 1) * exp_no
            command_dict_param['dither_expno'] = dither * exp_no
            self._alt_mount = azalt['alt']
            self._az_mount = azalt['az']
            self._az_dome = azalt['az']
            print(command_dict_param)
            tc = self.time_calc(command_name=command_dict['command_name'], command_dict_param=command_dict_param)
            if tc:
                comm_time = tc
            else:
                comm_time = 0.0
            self._time_length += comm_time
            return comm_time
        else:
            logger.debug(f'Cannot calculate time, lack of params')
            return 0.0

    def time_calc(self, command_name: str, command_dict_param: Dict[str, Any]) -> float or None:
        no_error = True
        param = self.available_param[self.telescope][command_name]
        for n, m in command_dict_param.items():
            if n not in param['coef'].keys():
                no_error = False
        if no_error:
            ret = 0
            for n, m in command_dict_param.items():
                ret += (m * param['coef'][n])
            ret += param['intercept']
            return ret
        else:
            return None


if __name__ == '__main__':
    c = CycleTimeCalc('dev')
    print(c.avialable_param_telesc)
    print(c.avialable_param_telesc_commands)
    d = {'command_name': 'OBJECT', 'kwargs': {'seq': '12/Red/1,3/Green/3,2/Blue/5', 'az': 12.0, 'alt':70.0}}
    print(c.calc_time(command_dict=d))
    print(c._time_length)
