from datetime import datetime
from abc import ABC, abstractmethod

from ob.address import Address
from ob.value import Value


class ValueSet(ABC):

    @abstractmethod
    def __init__(self, source):
        self.source = source  # źrudło z kąd pobieramy dane no IRIS czy MIKE czy jakiś iny teleskop

    @abstractmethod
    def getValue(self, address: Address, ts: datetime, delta: int) -> Value or None:
        pass

    @abstractmethod
    def getSource(self):
        pass

    @abstractmethod
    def setSource(self, source):
        pass
