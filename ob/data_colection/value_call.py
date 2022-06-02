import logging
from dataclasses import dataclass, fields, field
from datetime import datetime
from typing import ClassVar

from ob.data_colection.address import Address
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value import Value

logger = logging.getLogger(__name__)


@dataclass
class ValueExchange:
    STANDARD_KEYS: ClassVar[list] = []  # master keys that store essential data
    _CONVERTING_TYPES: ClassVar[list] = [Address, Value, ResponseError]  # TODO klasa po której te wszystkie dziedzicza i mająwszystkie to_dict()

    @classmethod
    def from_dict(cls, dict_):
        # TODO czy podczas tworzenia klast z słownika jak nie ma w nimwszystkich potrzebnych wartości to ma być błąd
        #  czy jakoś go obsłurzyc? MIKOŁAJ
        #  Jak przechwytywać to zmienić też w RequestSolver.get_answer
        """
        Cteate this class from given dict of fields. The dictionary must have all the necessary fields.
        Redundant fields are ignored.
        :param dict_: Dictionary witch class fields
        :return: instance of this class
        """
        class_fields = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in dict_.items() if k in class_fields})  # why warning? everything is good

    def to_dict(self) -> dict:
        """
        This method convert object to dictionary. If among the property of this class there are other classes that
        have to_dict() methods implanted, they will also be converted, creating a nested dictionary.
        :return: dictionary
        """
        d = {}
        for k, v in self.__dict__.items():
            if k in self.STANDARD_KEYS:
                if isinstance(v, datetime):
                    v = datetime.timestamp(v)
                if type(v) in self._CONVERTING_TYPES and hasattr(v, 'to_dict'):
                    d[k] = v.to_dict()
                else:
                    d[k] = v
        return d


@dataclass
class ValueRequest(ValueExchange):
    # master keys that store essential data
    STANDARD_KEYS: ClassVar[list] = list(set(ValueExchange.STANDARD_KEYS + ['address', 'timestamp', 'delta']))
    address: str or Address or dict
    timestamp: datetime or float  # now
    delta: float  #todo z konfiguracji domyslna wartosc
    index: int = field(init=False, default=0)

    def __post_init__(self):
        # check address
        if isinstance(self.address, dict):
            self.address = Address(**self.address)
        elif isinstance(self.address, Address):
            pass
        else:
            self.address = Address(self.address)  # I know, wrong typing but it must be so, raise AddressError here
        # check date
        if isinstance(self.timestamp, float):
            self.timestamp = datetime.fromtimestamp(self.timestamp)
        elif isinstance(self.timestamp, datetime):
            pass
        else:
            raise ValueError
        # check delta
        self.delta = float(self.delta)  # this raise ValueError if is wrong type


@dataclass
class ValueResponse(ValueExchange):
    # master keys that store essential data
    STANDARD_KEYS: ClassVar[list] = list(set(ValueExchange.STANDARD_KEYS + ['address', 'value', 'status', 'error']))
    address: str or Address
    value: Value or None
    status: bool = field(default=True)  # if false that mean response has some errors
    error: ResponseError or None = field(default=None)

    def __post_init__(self):
        if isinstance(self.address, dict):
            self.address = Address(**self.address)
        elif isinstance(self.address, Address):
            pass
        else:
            self.address = Address(self.address)  # I know, wrong typing but it must be so, raise AddressError here

        if isinstance(self.value, dict):
            self.value = Value(**self.value)
        elif self.value is None or isinstance(self.value, Value):
            pass
        else:
            raise ValueError

        if isinstance(self.error, dict):
            self.error = ResponseError(**self.error)
        elif self.error is None or isinstance(self.error, ResponseError):
            pass
        else:
            raise ValueError
