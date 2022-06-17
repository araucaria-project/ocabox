import asyncio
from dataclasses import dataclass
import logging
from asyncio import Task
from datetime import datetime, timedelta
from typing import List

from ob.data_colection.address import Address
from ob.data_colection.base_components.tree_base_provider import TreeBaseProvider
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.coded_error import TreeStructureError
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class TreeCache(TreeBaseProvider):

    def __init__(self, component_name: str, subcontractor: ProvidesResponseProtocol = None, **kwargs):
        super().__init__(component_name=component_name, subcontractor=subcontractor, **kwargs)
        # self.known_values: List[Tuple[Address, Value, Task]] = []  # list (address :Address, value: Value, task: Task)
        self.known_values: List[TreeCache._KnownValue] = []  # list (address :Address, value: Value, task: Task)
        self._max_recall = 1  # After how many times he waits for the previous task, he asks yourself.
        if self._max_recall < 1:
            logger.warning(f"The _max_recall value is lover than one. It is unacceptable so will be set to 1 !")
            self._max_recall = 1

    @dataclass
    class _KnownValue:
        address: Address
        value: Value
        task: Task or None

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        recall = kwargs.get('recall', 0)
        address = request.address
        known_value = self._find_in_known_values(address)
        value = known_value.value if self._value_meets_requirements(known_value, request.timestamp,
                                                                    request.delta) else None

        # found in known values
        if value:
            return value
        else:
            if recall > 0:
                # The newly downloaded value does not meet the requirements
                logger.info(f'Retry retrieving content from the cache but a value was not supplied by the previous '
                            f'task. Nr recall {recall} / {self._max_recall}')

        task = known_value.task
        # not found and no one asks about it
        if not task or task.done():
            known_value.task = None
            known_value.task = asyncio.current_task()
            raise TreeStructureError

        # not found but someone asks about it and waiting for answer
        if task and not task.done():
            if recall < self._max_recall:
                await task
                return await self.get_value(request, recall=recall + 1)

        logger.info(f"stop waiting for other task and try ask yourself")
        raise TreeStructureError

    def _on_subcontractor_return(self, result: ValueResponse):
        kv = self._find_in_known_values(result.address)
        self._update_known_value(result.address, result.value, kv)
        self._remove_the_value_lock(result.address, kv)

    def _find_in_known_values(self, address) -> _KnownValue or None:
        """
        This method check if value for given address exists in known values and return it.

        :param address: Address
        :return: object representing stored value for given address or None if not exists
        """
        # check if the value is in cache
        for kv in self.known_values:
            if kv.address == address:
                return kv
        #  return None if value is not in cache
        return None

    @staticmethod
    def _value_meets_requirements(kv: _KnownValue, ts: datetime, delta: float):
        """
        Method check if known value meets requirements and can be used to send client.

        :param kv: _KnownValue object
        :param ts: timestamp
        :param delta: allowable delay
        :return: Returns True if the conditions are met and False if not
        """
        #  check that the value meets the requirements
        t_delta = timedelta(seconds=delta)
        return not kv.value.is_expired(ts, t_delta)

    def _update_known_value(self, address: Address, value: Value, known_value: _KnownValue = None):
        """
        This method update known values.

        :param address: Address
        :param value: Value
        :param known_value: _KnownValue object. It is optional, it can be specified to limit the amount of searching a
            list of known values
        :return: None
        """
        # warning value can be None if response got error so check this first
        if value:
            kv = known_value if known_value else self._find_in_known_values(address)
            # if value isn't on list yet
            if not kv:
                kv = self._KnownValue(address=address, value=value, task=None)
                self.known_values.append(kv)
                return
            # if new provided data is earlier than the date currently stored in list
            if kv.value.ts < value.ts:
                kv.value = value

    def _remove_the_value_lock(self, address, known_value: _KnownValue = None):
        kv = known_value if known_value else self._find_in_known_values(address)
        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            logger.warning(f'Can not find current task for request')
            return
        if kv.task == current_task:
            kv.task = None
        else:
            logger.error(f'the current task is not a stored task')
