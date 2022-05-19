import copy
import logging
from datetime import datetime

from ob.data_colection.value import Value
from ob.data_colection.value_broker import ValueBroker
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.data_colection.value_set import ValueSet

logger = logging.getLogger(__name__)


class ValueCache(ValueSet):

    def __init__(self, source, source_address: str, subcontractor: ValueBroker = None):
        super().__init__(source, source_address, subcontractor)
        # todo source dla tego to bedzie klasa ktura dzwoni do alpaki
        self.known_values: list = []

    def get_source(self):
        return self.source

    def get_value(self, request: ValueRequest) -> Value or None:
        address = request.address
        return self._find_in_known_values(address[address.get_last_index()], request.timestamp, request.delta)

    def set_source(self, source):
        self.source = source

    def _find_in_known_values(self, value_name, ts: datetime, delta: float) -> Value or None:
        if delta < 0:
            return Value('ok', ts, 'string')
        return None

