import asyncio
import logging
import unittest
from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.resource_manager.resource import DomeAlpaca
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from test.data_colection.base_async_test import BaseAsyncTest

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ResourceTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.tree_cache = TreeCache('sample_name_cache', self.tao)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.rs = RequestSolver(self.tree_freezer)
        self.api_test = InternalClientAPI(request_solver=self.rs, user_name=f"DefaultTest")

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_resource_path(self):
        adr_path = "adr1.adr2.adr3"
        resource_name = "res_some"
        res = DomeAlpaca(source_name=resource_name, resource_name="some", nr=0, target_request=None,
                         address_path=adr_path)
        self.assertEqual(res.adr, adr_path + "." + resource_name)


class DomeAlpacaTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.tree_cache = TreeCache('sample_name_cache', self.tao)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.rs = RequestSolver(self.tree_freezer)
        self.api_test = InternalClientAPI(request_solver=self.rs, user_name=f"DefaultTest")

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()


class MountAlpacaTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.tree_cache = TreeCache('sample_name_cache', self.tao)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.rs = RequestSolver(self.tree_freezer)
        self.api_test = InternalClientAPI(request_solver=self.rs, user_name=f"DefaultTest")

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_get_telescope_name(self):
        """Test getting telescope unique name from parameters"""

        async def coro():
            rm = await self.tao.get_res_manager()
            # get from config
            mount = rm.get_resource(name=rm.MOUNT, nr=0)
            self.assertEqual(self.OBSERVATORY_NAME, mount.telescope_id)

        asyncio.run(coro())

    def test_get_configuration(self):
        """Test get configuration from config file"""
        async def coro():
            rm = await self.tao.get_res_manager()
            # get from config
            mount = rm.get_resource(name=rm.MOUNT, nr=0)
            self.assertEqual(15, mount.min_alt)
            self.assertEqual('2000', mount.epoch)

        asyncio.run(coro())


class FilterwheelAlpacaTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.tree_cache = TreeCache('sample_name_cache', self.tao)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.rs = RequestSolver(self.tree_freezer)
        self.api_test = InternalClientAPI(request_solver=self.rs, user_name=f"DefaultTest")

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_filters_configuration(self):
        """Test correctly getting filters definitions"""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            # get from config
            filterwheel2 = rm.get_resource(name=rm.FILTERWHEEL, nr=1)
            filters2 = await filterwheel2.get_filters()
            self.assertTrue(isinstance(filters2, dict))
            self.assertEqual(filters2, filterwheel2.properties.get("filters"))
            # get from alpaca
            filterwheel = rm.get_resource(name=rm.FILTERWHEEL, nr=0)
            filters = await filterwheel.get_filters()
            self.assertTrue(isinstance(filters, dict))
            self.assertTrue(filters)
            self.assertNotEqual(filters, filterwheel2.properties.get("filters"))
            await self.tree_freezer.stop()

        asyncio.run(coro())


if __name__ == '__main__':
    unittest.main()
