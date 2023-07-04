from typing import Dict, Any
from .ctdata import CTData
import logging
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeDataBuild(AbstractCycleTime):
    """
    This class represent cycle time data builder (collector)
    """
    def __init__(self, telescope_name: str):
        self._data_cont: Dict = {}
        super().__init__(telescope_name=telescope_name)

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

    def read_data_from_file(self):
        pass

    def save_to_log(self, container_name: str = 'default'):
        logger.debug(f'Data {container_name} saved to log')
        if container_name not in self._data_cont.keys():
            logger.error(f'can not save cycle time log to file, no data {container_name}')
        else:
            self._data_cont[container_name].insert_single_data('utc_date_stamp', str(self.timestamp().isoformat()))
            self._data_cont[container_name].insert_single_data('utc_time_stamp', str(self.timestamp().timestamp()))
            self.add_to_file(self.encode_data(self._data_cont[container_name].data), self.base_folder, self.raw_file_name)
