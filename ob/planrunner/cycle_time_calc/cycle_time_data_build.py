from typing import Dict, Any
from .ctdata import CTData
import logging
from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime


logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTimeDataBuild(AbstractCycleTime):
    """
    This class represent cycle time data builder (collector)
    """
    def __init__(self, telescope: str) -> None:
        self.telescope = telescope
        self._data: CTData = CTData()
        super().__init__()
        #self._mk_dirs()


    def insert_data(self, name: str, value: Any) -> None:
        logger.debug(f'Data inserted: {name} {value}')
        self._data.insert_single_data(name=name, value=value)

    def insert_data_dict(self, dict: Dict[str, Any]) -> None:
        logger.debug(f'Data inserted from dict: {dict}')
        self._data.insert_data_from_dict(dict=dict)

    def save_to_log(self) -> None:
        logger.debug(f'Data {self.telescope} saved to log')
        self._data.insert_single_data('utc_date_stamp', str(self.time_stamp().isoformat()))
        self._data.insert_single_data('utc_time_stamp', str(self.time_stamp().timestamp()))
        self.add_to_file(self.encode_data(self._data.data),
                         self.BASE_FOLDER_NAME, self.raw_file_name(telescope=self.telescope))
