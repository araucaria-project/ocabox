from datetime import datetime

from ob.address import Address
from ob.value import Value
from ob.value_set import ValueSet


class ValueStorage(ValueSet):
    def getValue(self, address: Address, ts: datetime, delta: int) -> Value or None:
        pass
