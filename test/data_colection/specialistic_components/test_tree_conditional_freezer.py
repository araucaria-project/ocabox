import asyncio
import logging
import time
import unittest
from typing import List, Tuple

from ob.data_colection.address import Address
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.coded_error import TreeStructureError
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest
from test.data_colection.sample_test_value_provider import SampleTestValueProvider

logger = logging.getLogger(__name__)


class TestTreeConditionalFreezer(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.v1, self.v2, *other = SampleTestValueProvider.SAMPLE_VALUES

        self.tree_provider2 = SampleTestValueProvider('sample_name2', 'provider2', [self.v1, self.v2])
        self.tree_cache = TreeCache('sample_name_cache', self.tree_provider2)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.tree_provider1 = TreeProvider('sample_name1', 'provider1', self.tree_freezer)
        self.max_refreshes = 3
        self.tree_freezer.set_max_refreshes(self.max_refreshes)
        self.time_interval = 0.2  # number of seconds to test the temporal aspects of the module

    def tearDown(self) -> None:
        super().tearDown()

    async def _start_stop_tree(self, coro):
        try:
            await self.tree_provider1.run()
            return await coro
        finally:
            await self.tree_provider1.stop()

    def test_empty_cache_unable_to_cache_value(self):
        """
        Test of the situation when the cache is empty, and it is asked for a value that it cannot initialize because
        it is not cachable
        """
        address = Address('.'.join([self.tree_provider1.get_source_name(),
                                    self.tree_provider2.get_source_name(),
                                    'new_val']))
        time_of_data_tolerance = 1
        request = ValueRequest(address, time.time(),
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_type='PUT',
                               request_data={'time_of_known_change': None},
                               cycle_query=True)

        response = asyncio.run(self._start_stop_tree(self.tree_provider1.get_response(request)))
        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, 4003)
        self.assertEqual(len(self.tree_cache._known_values), 0)
        self.assertEqual(self.tree_provider2.nr_requests, 1)  # There should only be one query because request is non
        # cacheable and should skip blocks: freezer and cache

    def test_empty_cache_able_to_cache_value(self):
        """
        Test of the situation when the cache is empty, and it will be asked for a value that it can initiate
        (value is cachable), but the provider does not return a value, but an error.
        """
        address = Address('.'.join([self.tree_provider1.get_source_name(),
                                    self.tree_provider2.get_source_name(),
                                    'value_error']))
        time_of_data_tolerance = self.time_interval

        request = ValueRequest(address, time.time(),
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_type='GET',
                               request_data={'time_of_known_change': None},
                               cycle_query=True)
        logger.warning('Time test started - may take a while to complete')
        start_time = time.time()
        response = asyncio.run(self._start_stop_tree(self.tree_provider1.get_response(request)))
        total_time = time.time() - start_time
        # Checks if the program does not send back the answer too quickly when the minimum time between successive
        # value updates is defined
        self.assertTrue(total_time > self.time_interval * self.max_refreshes)

        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(len(self.tree_cache._known_values), 1)

        # one for initialize and one for first refresh and plus self.max_refreshes
        self.assertEqual(self.tree_provider2.nr_requests, 1 + 1 + self.max_refreshes)

    def test_initialized_cache_unable_to_cache_value(self):
        """
        IMPORTANT TEST.\n
        Test the situation when the cache is initialized with a blank value and is requested for a value that it can
        be cached. This situation can occur when someone calls the address via GET request and then does it via PUT
        """
        address = Address('.'.join([self.tree_provider1.get_source_name(),
                                    self.tree_provider2.get_source_name(),
                                    'new_val']))
        time_of_data_tolerance = self.time_interval

        request = ValueRequest(address, time.time(),
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_type='PUT',
                               request_data={'time_of_known_change': None},
                               cycle_query=True)
        # initialize cache list witch empty value
        self.tree_cache._known_values.append(self.tree_cache._KnownValue(address=address, value=None,
                                                                         task=None, change_time=0))

        logger.warning('Time test started - may take a while to complete')
        start_time = time.time()
        response = asyncio.run(self._start_stop_tree(self.tree_provider1.get_response(request)))
        total_time = time.time() - start_time
        # Checks if the program does not send back the answer too quickly when the minimum time between successive
        # value updates is defined
        self.assertTrue(total_time > self.time_interval * self.max_refreshes)

        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(len(self.tree_cache._known_values), 1)

        # one for first refresh and plus self.max_refreshes
        self.assertEqual(self.tree_provider2.nr_requests, 1 + self.max_refreshes)

    def test_initialized_cache_able_to_get_value(self):
        """Test the situation when the cache is initialized with a blank value and is asked for a value that it can
                initialize but provider does not return a value, but an error"""
        address = Address('.'.join([self.tree_provider1.get_source_name(),
                                    self.tree_provider2.get_source_name(),
                                    'new_val']))
        time_of_data_tolerance = self.time_interval

        # set the 'raise_value_error' simulate situation when provider is offline and return error all time
        request = ValueRequest(address, time.time(),
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_type='GET',
                               request_data={'time_of_known_change': None, 'raise_value_error': True},
                               cycle_query=True)
        # initialize cache list witch empty value
        self.tree_cache._known_values.append(self.tree_cache._KnownValue(address=address, value=None,
                                                                         task=None, change_time=0))

        logger.warning('Time test started - may take a while to complete')
        start_time = time.time()
        response = asyncio.run(self._start_stop_tree(self.tree_provider1.get_response(request)))
        total_time = time.time() - start_time
        # Checks if the program does not send back the answer too quickly when the minimum time between successive
        # value updates is defined
        self.assertTrue(total_time > self.time_interval * self.max_refreshes)

        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(len(self.tree_cache._known_values), 1)

        # one for first refresh and plus self.max_refreshes
        self.assertEqual(self.tree_provider2.nr_requests, 1 + self.max_refreshes)

    def test_normal_work(self):
        pass

    def test_timeout(self):
        pass
