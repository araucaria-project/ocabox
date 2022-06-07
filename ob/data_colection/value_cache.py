import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from ob.data_colection.value import Value
from ob.data_colection.value_broker import ValueBroker
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class ValueCache():

    def __init__(self, source, source_address: str, subcontractor: ValueBroker = None):
        super().__init__(source, source_address, subcontractor)
        self.known_values: List[Tuple[str, Value]] = []  # list pair (name :str, value: Value)

    def get_source(self):
        return self.source

    def get_value(self, request: ValueRequest) -> Value or None:
        address = request.address
        known_value = self._find_in_known_values(address[address.get_last_index()], request.timestamp, request.delta)
        if known_value:
            return known_value

        return Value(23, datetime.now(), 'int')

    def set_source(self, source):
        self.source = source

    def _find_in_known_values(self, value_name, ts: datetime, delta: float) -> Value or None:
        # check if the value is in cache
        for n, v in self.known_values:
            if n == value_name:
                #  check that the value meets the requirements
                t_delta = timedelta(seconds=delta)
                return v if not v.is_expired(ts, t_delta) else None
        #  return None if value is not in cache
        return None
