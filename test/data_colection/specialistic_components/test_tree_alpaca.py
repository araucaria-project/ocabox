import asyncio
import logging
import time
import unittest

from ob.comunication.request_solver import RequestSolver
from ob.data_colection.address import Address
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.value_call import ValueRequest
from ob.ob_config import SingletonConfig
from ob.util_functions.asyncio_util_functions import wait_for_psce
from test.data_colection.base_async_test import BaseAsyncTest

logger = logging.getLogger(__name__.rsplit('.')[-1])


class TreeAlpacaTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'
    OBSERVATORY_DOWN_NAME = 'test_observatory_down'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.rs = RequestSolver(self.tao)

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_alpaca_call(self):
        """
        Test connection to the alpaca server. This test requires the alpaca server to be running in the background.
        """
        sample_alpaca_call = 'name'

        sample_components = SingletonConfig.get_config()['tree'][self.OBSERVATORY_NAME]['observatory'][
            'components'].get()
        component = list(sample_components.keys())[0]

        address = Address('.'.join([component, sample_alpaca_call]))
        request = ValueRequest(address, time.time())

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNotNone(response.value)
            self.assertTrue(isinstance(response.value.v, str))

        self.loop.run_until_complete(coro())

    def test_alpaca_wrong_call(self):
        sample_alpaca_call = 'no_existing_method'

        sample_components = SingletonConfig.get_config()['tree'][self.OBSERVATORY_NAME]['observatory'][
            'components'].get()
        component = list(sample_components.keys())[0]

        address = Address('.'.join([component, sample_alpaca_call]))
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

        sample_components = SingletonConfig.get_config()['tree'][self.OBSERVATORY_NAME]['observatory'][
            'components'].get()
        component = list(sample_components.keys())[0]

        address = Address('.'.join([component, sample_alpaca_call]))
        request = ValueRequest(address, time.time())

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNotNone(response.value)
            self.assertTrue(isinstance(response.value.v, str))

        self.loop.run_until_complete(coro())

    def test_too_short_address(self):
        """Test situation when incoming address is too short"""
        sample_alpaca_call = 'name'

        sample_components = SingletonConfig.get_config()['tree'][self.OBSERVATORY_NAME]['observatory'][
            'components'].get()
        component = list(sample_components.keys())[0]

        address = Address("block1.block2")
        request = ValueRequest(address, time.time())
        request.index = 2

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNone(response.value)
            self.assertFalse(response.status)
            self.assertTrue(response.error.code == 1001)

        self.loop.run_until_complete(coro())

    def test_get_resource(self):
        """Test method get_resources"""
        resources = self.tao.get_resources()
        self.assertEqual(resources, [('dibi_RESOURCE', ['dibi']), ('dome_RESOURCE', ['dome']),
                                     ('filterwheel_RESOURCE', ['filterwheel']),
                                     ('filterwheel2_RESOURCE', ['filterwheel2']),
                                     ('covercalibrator_RESOURCE', ['covercalibrator']),
                                     ('camera_RESOURCE', ['camera']),
                                     ('focuser_RESOURCE', ['focuser']),
                                     ('derotator_RESOURCE', ['derotator']),
                                     ('switch_RESOURCE', ['switch']),
                                     ('safetymonitor_RESOURCE', ['safetymonitor'])])

    def test_get_res_manager(self):
        """Test method get_resource_manager()"""
        from ob.data_colection.resource_manager.resource_manager import ResourceManager
        manager: ResourceManager = asyncio.run(self.tao.get_res_manager())
        self.assertTrue(isinstance(manager, ResourceManager))
        self.assertEqual(len(manager._resources), 2)
        # todo tu skonczyłem ten test nie przechodzi
    def test_alpaca_not_response(self):
        """Test situation when alpaca server is down."""
        # Module with connection to no responding Alpaca
        tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_DOWN_NAME)

        sample_alpaca_call = 'name'
        timeout = 1
        sample_components = SingletonConfig.get_config()['tree'][self.OBSERVATORY_NAME]['observatory'][
            'components'].get()
        component = list(sample_components.keys())[0]

        address = Address('.'.join([component, sample_alpaca_call]))
        request = ValueRequest(address, time.time(), request_timeout=timeout)

        async def coro():
            try:
                response = await wait_for_psce(tao.get_response(request), timeout=timeout+2)
            except asyncio.TimeoutError:
                # if this error was raise that mean alpaca module is not working correctly
                raise RuntimeError
            self.assertIsNone(response.value)
            self.assertFalse(response.status)
            self.assertIsNotNone(response.error)
            self.assertTrue(response.error.code == 4005)

        self.loop.run_until_complete(coro())

    def test_get_configuration(self):
        """Test method get_configuration()"""
        provider = self.tao
        cfg = provider.get_configuration()
        self.assertListEqual(list(cfg.keys()), ["sample_component"])
        self.assertListEqual(list(cfg.get("sample_component").keys()), ["child", "type", "config"])
        self.assertEqual(cfg.get("sample_component").get("type"), "TreeAlpacaObservatory")
        self.assertDictEqual(cfg.get("sample_component").get("child"), {})


if __name__ == '__main__':
    unittest.main()
