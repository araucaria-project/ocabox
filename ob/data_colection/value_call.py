import logging
from dataclasses import dataclass, fields
from datetime import datetime
from typing import ClassVar

from ob.data_colection.address import Address
from ob.data_colection.value import Value

logger = logging.getLogger(__name__)


@dataclass
class ValueExchange:
    STANDARD_KEYS: ClassVar[list] = []  # master keys that store essential data
    _CONVERTING_TYPES: ClassVar[list] = [Address, Value]

    @classmethod
    def from_dict(cls, dict_):
        # TODO czy podczas tworzenia klast z słownika jak nie ma w nimwszystkich potrzebnych wartości to ma być błąd
        #  czy jakoś go obsłurzyc? MIKOŁAJ
        """
        Cteate this class from given dict of fields. The dictionary must have all the necessary fields.
        Redundant fields are ignored.
        :param dict_: Dictionary witch class fields
        :return: instance of this class
        """
        class_fields = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in dict_.items() if k in class_fields})  # why warning? everything is good

    # TODO Czy taka metoda zmieniająca klase na dict rekuręcyjnie jest poprawna? problem moze się pojawić jeśli
    #  przypadkiem dodamy obiekt który ma taką metodę ale robi ona co innego ale czy może cos takiego się wydarzyć?
    #  Może jednak wysyłać obiekty przec zmq a jkak będzie potrzebny inny jęcyk to i tak te obiekty się przepisze na
    #  tamten język i bedzie ok MIKOŁAJ
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
    address: str or Address
    timestamp: datetime
    delta: float
    index: int = 0

    def __post_init__(self):
        if isinstance(self.address, str):
            self.address = Address(self.address)
        if isinstance(self.address, dict):
            self.address = Address(**self.address)
        if isinstance(self.timestamp, float):
            self.timestamp = datetime.fromtimestamp(self.timestamp)


@dataclass
class ValueResponse(ValueExchange):
    # master keys that store essential data
    STANDARD_KEYS: ClassVar[list] = list(set(ValueExchange.STANDARD_KEYS + ['address', 'value']))
    address: str or Address
    value: Value or None

    def __post_init__(self):
        if isinstance(self.address, str):
            self.address = Address(self.address)
        if isinstance(self.address, dict):
            self.address = Address(**self.address)
        if isinstance(self.value, dict):
            self.value = Value(**self.value)
