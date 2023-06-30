from typing import Dict, Any
from ocaboxapi.observatory import Observatory
from .ctdata import CTData
import logging
from .abstract_cycle_time import AbstractCycleTime


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeDataBuild(AbstractCycleTime):
    """
    This class represent cycle time data builder (collector)
    """
    def __init__(self, observatory: Observatory = None):
        self._data_cont: Dict = {}
        super().__init__(observatory=observatory)
        self._mk_dirs()

    def insert_data(self, name: str, value: Any, container_name: str = 'default') -> None:
        logger.debug(f'Data inserted: {name} {value} {container_name}')
        if container_name not in self._data_cont.keys():
            self._data_cont[container_name] = CTData(container_name=container_name)
        self._data_cont[container_name].insert_single_data(name=name, value=value)

    def insert_data_dict(self, dict: Dict[str, Any], container_name: str = 'default') -> None:
        logger.debug(f'Data inserted from dict: {dict} {container_name}')
        if container_name not in self._data_cont.keys():
            self._data_cont[container_name] = CTData(container_name=container_name)
        self._data_cont[container_name].insert_data_from_dict(dict=dict)

    def save_to_log(self, container_name: str = 'default'):
        logger.debug(f'Data {container_name} saved to log')
        if container_name not in self._data_cont.keys():
            logger.error(f'can not save cycle time log to file, no data {container_name}')
        else:
            self._data_cont[container_name].insert_single_data('utc_date_stamp', str(self.timestamp().isoformat()))
            self._data_cont[container_name].insert_single_data('utc_time_stamp', str(self.timestamp().timestamp()))
            self.to_log_file(self._data_cont[container_name].data, self.log_folder, self.FILE_NAMES['raw_data'])
