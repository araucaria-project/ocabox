import asyncio
import datetime
import time
import unittest
from typing import List, Tuple

from ob.data_colection.address import Address
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.coded_error import TreeStructureError
from ob.data_colection.specialistic_components.tree_cache import TreeCache
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest


class TreeCacheTest(unittest.TestCase):
    class SampleTestValueProvider(TreeProvider):
        RESPONSE_DELAY = 0

        async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
            address = request.address
            value_name = address[address.get_last_index()]
            self.count_current_tasks += 1
            self.count_tasks += 1
            await asyncio.sleep(self.response_delay)
            self.count_current_tasks -= 1
            for n, v in self.test_values:
                if value_name == n:
                    return v
            if value_name == 'error':
                raise TreeStructureError
            return None

        def __init__(self, component_name: str, source_name: str, test_values: List[Tuple[str, Value]],
                     subcontractor: ProvidesResponseProtocol = None, **kwargs):
            self.response_delay = self.RESPONSE_DELAY
            self.count_current_tasks = 0
            self.count_tasks = 0
            self.test_values: List[Tuple[str, Value]] = test_values
            super().__init__(component_name=component_name, source_name=source_name, subcontractor=subcontractor,
                             **kwargs)

    def setUp(self):
        super().setUp()
        self.v1 = ('val1', Value(1, datetime.datetime(2022, 5, 20, 1, 1, 1)))
        self.v2 = ('val2', Value(2, datetime.datetime(2022, 5, 20, 2, 2, 2)))

        self.tree_provider2 = self.SampleTestValueProvider('sample_name2', 'provider2', [self.v1, self.v2])
        self.tree_cache = TreeCache('sample_name_cache', self.tree_provider2)
        self.tree_provider1 = TreeProvider('sample_name1', 'provider1', self.tree_cache)

    def tearDown(self) -> None:
        super().tearDown()

    def test__value_meets_requirements(self):
        """
        Test method _value_meets_requirements()
        :return:
        """
        address = Address('.'.join(['sample_address', self.v1[0]]))
        kv = TreeCache._KnownValue(address, self.v1[1], None)

        expected_date = self.v1[1].ts + datetime.timedelta(seconds=10)
        result = TreeCache._value_meets_requirements(kv, expected_date, 20)
        self.assertTrue(result)
        result = TreeCache._value_meets_requirements(kv, expected_date, 10)
        self.assertTrue(result)
        result = TreeCache._value_meets_requirements(kv, expected_date, 5)
        self.assertFalse(result)

    def test__update_known_value(self):
        """
        Test method _update_known_value()
        :return:
        """
        address = Address('.'.join(['sample_address', self.v1[0]]))
        tc = TreeCache('sample_name', None)

        # test add any value
        self.assertTrue(len(tc._known_values) == 0)
        tc._update_known_value(address, self.v1[1])
        self.assertTrue(len(tc._known_values) == 1)
        self.assertEqual(tc._known_values[0].value, self.v1[1])
        self.assertEqual(tc._known_values[0].address, address)

        # test add new value
        address2 = Address('.'.join(['sample_address', self.v2[0]]))
        tc._update_known_value(address2, self.v2[1])
        self.assertTrue(len(tc._known_values) == 2)

        # test change value to newer
        address2 = Address('.'.join(['sample_address', self.v2[0]]))
        v2 = self.v2[1].__copy__()
        v2.ts = v2.ts + datetime.timedelta(10)
        v2.v = v2.v + 10
        tc._update_known_value(address2, v2)

        self.assertTrue(len(tc._known_values) == 2)
        self.assertEqual(tc._known_values[1].value, v2)
        self.assertEqual(tc._known_values[1].address, address2)

        # test do not change value to older
        address2 = Address('.'.join(['sample_address', self.v2[0]]))
        v3 = self.v2[1].__copy__()
        v3.ts = v3.ts - datetime.timedelta(10)
        v3.v = v3.v + 20
        tc._update_known_value(address2, v3)

        self.assertTrue(len(tc._known_values) == 2)
        self.assertNotEqual(tc._known_values[1].value, v3)
        self.assertEqual(tc._known_values[1].address, address2)

    def test_flow_empty_cache(self):
        """
        Test of information flow through TreeCache block. Ask about any value when cache is empty.

        :return:
        """

        address = Address('.'.join([self.tree_provider1.get_source_name(), self.tree_provider2.get_source_name(),
                                    self.v1[0]]))
        request = ValueRequest(address, self.v1[1].ts)

        # ask about any value when cache is empty
        response = asyncio.run(self.tree_provider1.get_response(request))
        self.assertEqual(response.value, self.v1[1])

    def test_flow_get_from_cache(self):
        """
        Test of information flow through TreeCache block. Ask about any value when cache is empty.

        :return:
        """

        address = Address('.'.join([self.tree_provider1.get_source_name(), self.tree_provider2.get_source_name(),
                                    self.v1[0]]))
        request = ValueRequest(address, self.v1[1].ts)

        # get first time and save in cache
        response = asyncio.run(self.tree_provider1.get_response(request))

        # change value returned by provider but set the same timestamp
        new_value = self.tree_provider2.test_values[0][1].__copy__()  # chere change return value in lase component
        new_value.v += 20
        self.tree_provider2.test_values[0] = (self.tree_provider2.test_values[0][0], new_value)

        # get value again, value should be provided by cache witch old value
        response = asyncio.run(self.tree_provider1.get_response(request))
        self.assertEqual(response.value.v, self.v1[1].v)

    def test_flow_no_repeat_answer(self):
        """
        A test that checks if the cache has no value and several tasks ask for it at the same time, then only one task
        should ask the provider and the rest should wait and download from the cache.

        :return:
        """
        self.tree_provider2.response_delay = 1
        address = Address('.'.join([self.tree_provider1.get_source_name(), self.tree_provider2.get_source_name(),
                                    self.v1[0]]))
        request = ValueRequest(address, self.v1[1].ts)
        nr_of_requests = 3

        # sample_list_request = [request for _ in range(nr_of_requests)]  # list witch 10 requests

        async def coro():
            request_tasks = [asyncio.create_task(self.tree_provider1.get_response(request)) for _ in
                             range(nr_of_requests)]
            time_start = time.time()

            await asyncio.sleep(0)
            self.assertTrue(self.tree_provider2.count_current_tasks == 1)
            for t in request_tasks:
                await t
            time_end = time.time()
            self.assertTrue(self.tree_provider2.count_tasks == 1)
            self.assertTrue(time_end - time_start < self.tree_provider2.response_delay * nr_of_requests)

        asyncio.run(coro())


if __name__ == '__main__':
    unittest.main()
