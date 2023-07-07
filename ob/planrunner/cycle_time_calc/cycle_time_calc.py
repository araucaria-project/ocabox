from typing import Dict, Any, List
import logging
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
import datetime
from pyaraucaria.coordinates import ra_dec_2_az_alt, ra_to_decimal, dec_to_decimal

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeCalc(AbstractCycleTime):
    """
    This class represent cycle time calculator
    """

    def __init__(self, telescope: str) -> None:
        self.available_param: Dict[str, Dict[str, Any]] = {}
        self._rmode: int = 0
        self._current_filter: str = ''
        self._alt_mount: float = 70.0
        self._az_mount: float = 0.0
        self._az_dome: float = 0.0
        self.telescope = telescope
        self._time_length: float = 0.0
        self._start_time: datetime.datetime =  datetime.datetime.utcnow()
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

    def _get_params(self) -> None:
        for t in CycleTimeCalc.get_list_telesc(file_type='train_param'):
            self.available_param[t] = {}
            for c in CycleTimeCalc.get_list_commands(telescope=t, file_type='train_param'):
                data = CycleTimeCalc.get_last_param(telescope=t, command=c)
                self.available_param[t][c] = data

    @staticmethod
    def get_last_param(telescope: str, command: str) -> Dict[str, Any]:
        data = CycleTimeCalc.read_file(CycleTimeCalc.BASE_FOLDER_NAME,
                                        CycleTimeCalc.train_param_file_name(telescope=telescope, command=command))
        return CycleTimeCalc.parse_data(data=data)[-1]

    def set_start_rmode(self, rmode: int) -> None:
        self._rmode = rmode

    def set_start_time(self, utc_time_stamp: datetime.datetime) -> None:
        self._start_time = utc_time_stamp

    def set_telescope_start_az_alt(self, az: float, alt: float) -> None:
        self._alt_mount = alt
        self._az_mount = az

    def set_dome_start_az(self, az: float) -> None:
        self._az_dome = az

    def _mount_altaz_target(self, command_dict: Dict[str, Any]) -> Dict[str, float] or None:
        altaz = None
        # ++++++TODO DO VENTUALLY SKIPPING OPERATIONS ZERO TIME ?++++++
        # TODO This OCA should be taken from settings
        OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
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
        else:
            ra = None
            dec = None
        if (ra is not None) and (dec is not None):
            az, alt = ra_dec_2_az_alt(ra=ra_to_decimal(ra),
                                      dec=dec_to_decimal(dec),
                                      longitude=OCA['longitude'],
                                      latitude=OCA['latitude'],
                                      elevation=OCA['elevation'],
                                      epoch='2000',
                                      time=self._start_time)
            altaz = {'az': az, 'alt': alt}
        if 'kwargs' in command_dict.keys() and (ra is None) and (dec is None):
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
            command_dict_param['rmmode_expno'] = (self._rmode + 1) * exp_no
            command_dict_param['dither_expno'] = dither * exp_no
            self._alt_mount = azalt['alt']
            self._az_mount = azalt['az']
            self._az_dome = azalt['az']
            self._current_filter = CycleTimeCalc.last_filter(command_dict)
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

    @property
    def time_lenght_sec(self) -> float:
        return self._time_length

    @property
    def time_lenght_min(self) -> float:
        return round(self._time_length/60, 1)

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
    d = {'command_name': 'OBJECT', 'kwargs': {'seq': '12/Red/1,3/Green/3,2/Blue/5', 'az': 12.0, 'alt':70.0}}
    print(c.calc_time(command_dict=d))
    print(c._time_length)
