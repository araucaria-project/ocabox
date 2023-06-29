from typing import Dict, List, Any, Callable
import os
from ocaboxapi.observatory import Observatory
import logging
import datetime
import time

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeCalc:

    def __init__(self, observatory: Observatory):
        self._data_file_name: str or None = 'default.log'
        self._data_provider_address:  str or None = None
        self._data_provider_name: str or None = None
        self._data_cont: Dict = {}
        self.observatory = observatory
        super().__init__()
        self._mk_dirs()


    def _mk_dirs(self):
        os.makedirs(self.log_folder, exist_ok=True)

    @property
    def log_folder(self):
        return os.path.expanduser(self.observatory.get_app_cfg('base_cycle_time_calc_dir', f'~/.oca/cycle_time_calc'))

    def set_data_file_name(self, data_file_name: str):
        self._data_file_name = data_file_name

    def insert_data(self, name: str, value: Any, container_name: str = 'default') -> None:
        if container_name not in self._data_cont.keys():
            self._data_cont[container_name] = CTData(container_name=container_name)
        self._data_cont[container_name].insert_single_data(name=name, value=value)

    def insert_data_dict(self, dict: Dict[str, Any], container_name: str = 'default') -> None:
        if container_name not in self._data_cont.keys():
            self._data_cont[container_name] = CTData(container_name=container_name)
        self._data_cont[container_name].insert_data_from_dict(dict=dict)

    def to_log_file(self, data: str):
        f = open(os.path.join(self.log_folder, self._data_file_name), "a")
        f.write(f'{data}')
        f.write('\n')
        f.close()


    def timestamp(self) -> datetime:
        return datetime.datetime.utcnow()

    def save_to_log(self, container_name: str = 'default'):
        if container_name not in self._data_cont.keys():
            logger.error(f'can not save cycle time log to file, no data {container_name}')
        else:
            self._data_cont[container_name].insert_single_data('utc_date_stamp', str(self.timestamp().isoformat()))
            self._data_cont[container_name].insert_single_data('utc_time_stamp', str(self.timestamp().timestamp()))
            self.to_log_file(self._data_cont[container_name].data)


class AbstractCycleTime:
    pass



class CommandCycleTime(AbstractCycleTime):
    pass


class CTData:

    def __init__(self, container_name: str = 'default'):
        self._data: Dict[str, Any] = {}
        self.container_name = container_name
        super().__init__()

    def insert_single_data(self, name: str, value: Any):
        self._data[name] = value

    def insert_data_from_dict(self, dict: Dict[str, Any]):
        self._data = self._data | dict

    @property
    def data(self) -> Dict[str, Any]:
        return self._data
