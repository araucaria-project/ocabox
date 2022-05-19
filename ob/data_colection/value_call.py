import logging
from dataclasses import dataclass, fields
from datetime import datetime
from typing import ClassVar

from ob.data_colection.address import Address
from ob.data_colection.value import Value

logger = logging.getLogger(__name__)


@dataclass
class ValueExchange:
    pass


@dataclass
class ValueRequest(ValueExchange):
    STANDARD_REQUEST_KEYS: ClassVar[list] = ['address', 'timestamp', 'time_range']
    address: str or Address
    timestamp: datetime
    delta: float
    index: int = 0

    def __post_init__(self):
        if isinstance(self.address, str):
            self.address = Address(self.address)
        if isinstance(self.timestamp, float):
            self.timestamp = datetime.fromtimestamp(self.timestamp)

    @classmethod
    def from_dict(cls, dict_):
        class_fields = {f.name for f in fields(cls)}
        return ValueRequest(**{k: v for k, v in dict_.items() if k in class_fields})


@dataclass
class ValueResponse(ValueExchange):
    STANDARD_RESPONSE_KEYS: ClassVar[list] = ['address', 'value']
    address: str or Address
    value: Value or None

    def __post_init__(self):
        if isinstance(self.address, str):
            self.address = Address(self.address)
        if isinstance(self.value, dict):
            self.value = Value(**self.value)
