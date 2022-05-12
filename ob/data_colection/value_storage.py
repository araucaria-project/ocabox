from datetime import datetime

from ob.data_colection.address import Address
from ob.data_colection.value import Value
from ob.data_colection.value_set import ValueSet


class ValueStorage(ValueSet):
    def getValue(self, address: Address, ts: datetime, delta: int) -> Value or None:
        pass
