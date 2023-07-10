from typing import Dict, Any, List
import logging
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
import datetime
from pyaraucaria.coordinates import ra_dec_2_az_alt, ra_to_decimal, dec_to_decimal
import time

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeCalc(AbstractCycleTime):
    """
    This class represent cycle time calculator (CTC).
    CTC base on machine learning module.
    To prepare proper parameters, CTC need steps:
    1. CycleTimeDataBuild is implemented inside planrunner, mostly in Command and NightPlan classes, to get all need
     info a parameters values. After collection it save data to files (every telescope in different file).
    2. CycleTimeDataClean is run at end of night program (not skipped program) to select, clean, and distributed to
     separate files. Module separate commands and telescopes to different files, and it is taking only data from
     complete programs (nights) to prevent some error and incomplete data. It also has mechanism to do not take
     data from same nights, to do not double operations.
    3. CycleTimeTrain is also run at end of night program (not skipped program). It is machine learning module built
     on linear regression. Parameters used to training are selected with care and supported by analyses. To aloud to
     train data, it has to be at least 10 records. If there is more data, the parameters will be more accurate.
    4. CycleTimeCalc is main class, used to calculate cycle time. Calculator use trained parameters prepared from
     previous observations. If there is no parameters to use, calculator backs 0.0 time length. For WAIT command
     calculator backs time strait, without any other calc. Calculator sets start_time at time when instance is call,
     but it can be changed by set_start_time. This parameter is important, because it will be taken to calculate
     telescope position from ra and dec coordinates. To make calculation more accurate, please also use
     set_observatory_location (default is oca), set_epoch (default is 2000), set_start_rmode (default is 0),
     set_telescope_start_az_alt (default is 0 70) and set_dome_start_az (default is 0). If You want to calculate
     if operations are below alt limit (and get 0.0 time because of skipping) please set set_skipping to True.
     You can also change alt limit by alt_limit method (default is set to 15.0).
     Example:
         c = CycleTimeCalc('dev')
         c.set_telescope_start_az_alt(az=120.0, alt=60.0)
         c.set_skipping(skipping=True)
         com_1 = {'command_name': 'OBJECT', 'kwargs': {'seq': '12/Red/1,3/Green/3,2/Blue/5', 'az': 12.0, 'alt':70.0}}
         c.calc_time(command_dict=com_1) --> you get time for com_1
         com_2 = {'command_name': 'WAIT', 'kwargs': {'wait': 40}}
         c.calc_time(command_dict=com_2) --> you get time for com_2
         c.time_lenght_min() --> you get time lenght for all operations (full cycle) in minutes
         c.finnish_time_utc() --> you get utc date_time when program will finish
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
        self._epoch: str = '2000'
        self._skipping: bool = False
        self._alt_limit: float = 15.0
        self._observatory_location: Dict[str, Any] = {'latitude': -24.598056,
                                                      'longitude': -70.196389,
                                                      'elevation': 2817}
        self._start_time: datetime.datetime = datetime.datetime.utcnow()
        self._mk_dirs()
        self._get_params()
        super().__init__()

    def set_observatory_location(self, location: Dict[str, Any]) -> None:
        """
        Set observatory location, default is oca location
        :param location: dict of location, like: {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
        """
        self._observatory_location = location

    def set_epoch(self, epoch: str) -> None:
        """
        Set epoch for ra dec coordinates, default: '2000'
        :param epoch: epoch in str format, example: '2000'
        """
        self._epoch = epoch

    def set_alt_limit(self, alt_limit: float) -> None:
        self._alt_limit = alt_limit

    def set_skipping(self, skipping: bool) -> None:
        self._skipping = skipping

    @property
    def avialable_param_telesc(self) -> Dict[str, Any] or None:
        if self.telescope in self.available_param.keys():
            return self.available_param[self.telescope]
        else:
            return None

    @property
    def avialable_param_telesc_commands(self) -> List[str]:
        li = []
        if self.avialable_param_telesc:
            for ke, val in self.avialable_param_telesc.items():
                li.append(ke)
        for n in CycleTimeCalc.NO_TRAIN_COMMANDS:
            if n in li:
                li.remove(n)
        return li

    def _get_params(self) -> None:
        for t in CycleTimeCalc.get_list_telesc(file_type='train_param'):
            self.available_param[t] = {}
            for co in CycleTimeCalc.get_list_commands(telescope=t, file_type='train_param'):
                data = CycleTimeCalc.get_last_param(telescope=t, command=co)
                self.available_param[t][co] = data

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
        """
        Method calculate alt az from command dictionary
        :param command_dict: command dict parsed by pyaraucaria obs_plan_parser
        :return: calculated alt az
        """
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
        else:
            ra = None
            dec = None
        if (ra is not None) and (dec is not None):
            az, alt = ra_dec_2_az_alt(ra=ra_to_decimal(ra),
                                      dec=dec_to_decimal(dec),
                                      longitude=self._observatory_location['longitude'],
                                      latitude=self._observatory_location['latitude'],
                                      elevation=self._observatory_location['elevation'],
                                      epoch=self._epoch,
                                      time=self._start_time.timestamp() + self._time_length)
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
                if (azalt['alt'] >= self._alt_limit) or (azalt['alt'] < self._alt_limit and self._skipping == False):
                    mount_alt_az_dist = CycleTimeCalc.alt_az_distance(start_alt=self._alt_mount,
                                                                      end_alt=azalt['alt'],
                                                                      start_az=self._az_mount,
                                                                      end_az=azalt['az'])
                    dome_az_dist = CycleTimeCalc.az_distance(start=self._az_dome, end=azalt['az'])
                    self._alt_mount = azalt['alt']
                    self._az_mount = azalt['az']
                    self._az_dome = azalt['az']
                else:
                    logger.debug(f'Alt is under lower limit, no time calculation')
                    return 0.0
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
            self._current_filter = CycleTimeCalc.last_filter(command_dict)
            time_cal = self._calc_time(command_name=command_dict['command_name'], command_dict_param=command_dict_param)
            if time_cal:
                comm_time = time_cal
            else:
                comm_time = 0.0
            self._time_length += comm_time
            return comm_time
        elif command_dict['command_name'] in CycleTimeCalc.NO_TRAIN_COMMANDS:
            if command_dict['command_name'] == 'WAIT':
                if 'kwargs' in command_dict.keys():
                    if 'wait' in command_dict['kwargs'].keys():
                        t = float(command_dict['kwargs']['wait'])
                        self._time_length += t
                        return t
                    if 'ut' in command_dict['kwargs'].keys():
                        d = datetime.datetime.fromtimestamp(self._start_time.timestamp() + self._time_length).strftime(
                            '%Y-%m-%d')
                        myDate = f"{d} {str(command_dict['kwargs']['ut'])}"
                        target_t = time.mktime(datetime.datetime.strptime(myDate, "%Y-%m-%d %H:%M:%S").timetuple())
                        if target_t >= (self._start_time.timestamp() + self._time_length):
                            t = float(target_t - (self._start_time.timestamp() + self._time_length))
                            self._time_length += t
                            return t
                        else:

                            logger.debug(f'Cannot calculate time, time in past')
                            return 0.0
                    else:
                        logger.debug(f'Cannot calculate time, no kwarg')
                        return 0.0
                else:
                    logger.debug(f'Cannot calculate time, no kwargs')
                    return 0.0
            else:
                logger.debug(f'Cannot calculate time, command not recognized')
                return 0.0
        else:
            logger.debug(f'Cannot calculate time, lack of params')
            return 0.0

    @property
    def time_lenght_sec(self) -> float:
        return self._time_length

    @property
    def time_lenght_min(self) -> float:
        return round(self._time_length/60, 1)

    def finnish_time_utc(self) -> str:
        return str(self._start_time + datetime.timedelta(seconds=self._time_length))

    def _calc_time(self, command_name: str, command_dict_param: Dict[str, Any]) -> float or None:
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
    #d = {'command_name': 'WAIT', 'kwargs': {'seq': '12/Red/1,3/Green/3,2/Blue/5', 'az': 12.0, 'alt':70.0}}
    d = {'command_name': 'WAIT', 'kwargs': {'ut': '08:48:00'}}
    print(c.calc_time(command_dict=d))
    # print(c._time_length)
    # print(c.finnish_time_from_now_utc)
