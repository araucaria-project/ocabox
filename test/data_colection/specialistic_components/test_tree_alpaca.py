import asyncio
import logging
import time
import unittest

from ob.data_colection.address import Address
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.value_call import ValueRequest
from ob.ob_config import SingletonConfig
from test.data_colection.base_async_test import BaseAsyncTest

logger = logging.getLogger(__name__)


class TreeAlpacaTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_alpaca_call(self):
        """
        Test connection to the alpaca server. This test requires the alpaca server to be running in the background.
        """
        sample_alpaca_call = 'name'

        sample_components = SingletonConfig.get_config()[self.OBSERVATORY_NAME]['observatory']['components'].get()
        component = list(sample_components.keys())[0]

        address = Address('.'.join([self.OBSERVATORY_NAME, component, sample_alpaca_call]))
        request = ValueRequest(address, time.time())

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNotNone(response.value)
            self.assertTrue(isinstance(response.value.v, str))

        self.loop.run_until_complete(coro())

    def test_alpaca_wrong_call(self):
        sample_alpaca_call = 'no_existing_method'

        sample_components = SingletonConfig.get_config()[self.OBSERVATORY_NAME]['observatory']['components'].get()
        component = list(sample_components.keys())[0]

        address = Address('.'.join([self.OBSERVATORY_NAME, component, sample_alpaca_call]))
        request = ValueRequest(address, time.time())

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNone(response.value)
            self.assertFalse(response.status)
            self.assertIsNotNone(response.error)
            self.assertTrue(response.error.code == 2002)

        self.loop.run_until_complete(coro())

    def test_change_address(self):
        """Test situation when address alpaca module is different from the name of the observatory"""
        sample_alpaca_call = 'name'

        sample_components = SingletonConfig.get_config()[self.OBSERVATORY_NAME]['observatory']['components'].get()
        component = list(sample_components.keys())[0]

        address = Address('.'.join([self.OBSERVATORY_NAME, component, sample_alpaca_call]))
        request = ValueRequest(address, time.time())

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNotNone(response.value)
            self.assertTrue(isinstance(response.value.v, str))

        self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()
