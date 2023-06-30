from typing import Dict, List, Any, Callable
import logging
logger = logging.getLogger(__name__.rsplit('.')[-1])


class CTData:
    """
    This class represent cycle time data
    """

    def __init__(self, container_name: str = 'default'):
        self._data: Dict[str, Any] = {}
        self.container_name = container_name
        super().__init__()

    def insert_single_data(self, name: str, value: str):
        self._data[name] = str(value)

    def insert_data_from_dict(self, dict: Dict[str, Any]):
        self._data = self._data | dict

    @property
    def data(self) -> Dict[str, Any]:
        return self._data