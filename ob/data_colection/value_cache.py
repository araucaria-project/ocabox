from datetime import datetime

from ob.data_colection.address import Address
from ob.data_colection.value import Value
from ob.data_colection.value_set import ValueSet


class ValueCache(ValueSet):

    def __init__(self, source):
        super().__init__(source)

        self.known_values: list = []

    def getValue(self, address: Address, ts: datetime, delta: int) -> Value or None:
        # TODO get value z teleskopu gdzieś tam łącząc się z alpaka
        return Value(12, datetime.now())

    def getSource(self):
        return self.source

    def setSource(self, source):
        self.source = source

    def _find_in_known_values(self, address: Address, ts: datetime):
        pass
