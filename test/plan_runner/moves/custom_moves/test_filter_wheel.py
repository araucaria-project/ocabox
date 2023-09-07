import asyncio
import random
import time
import unittest

from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.planrunner.ern.moves.custom_moves.filter_wheel import FilterWheel
from ob.planrunner.ern.plan_data import PlanData
from test.data_colection.base_async_test import BaseAsyncTest


class FilterWheelTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.tree_cache = TreeCache('sample_name_cache', self.tao)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.rs = RequestSolver(self.tree_freezer)
        self.tao.target_requests = self.rs
        self.api_test = InternalClientAPI(request_solver=self.rs, user_name=f"DefaultTest")

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_set_filter(self):
        """Test set filter"""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            plan_data = PlanData(access_resource_manager=rm, client_api=self.api_test)

            names = (await self.api_test.get_async(f"{rm.get_resource(rm.FILTERWHEEL).adr}.names")).value.v
            self.assertTrue(names)
            self.assertTrue(isinstance(names, list))
            self.assertTrue(len(names) > 0)
            targ_filter = names[random.randint(0, len(names) - 1)]

            fw = FilterWheel(filter_=targ_filter, plan_data=plan_data)
            await fw.a_init()
            # main method to make move
            start_time = time.time()
            await fw.run()
            self.assertTrue(time.time() - start_time < 0.5)  # method run() should make immediately
            await fw.wait()
            self.assertFalse(fw.error)  # finish witch no errors
            result = await self.api_test.get_async(f"{rm.get_resource(rm.FILTERWHEEL).adr}.position")
            self.assertEqual(result.value.v, names.index(targ_filter))
            self.assertEqual(fw.progress, 1)
            await self.tree_freezer.stop()

        asyncio.run(coro())

    def test_no_filter(self):
        """Test situation when as filter is given None"""
        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            plan_data = PlanData(access_resource_manager=rm, client_api=self.api_test)
            targ_filter = None

            fw = FilterWheel(filter_=targ_filter, plan_data=plan_data)
            self.assertTrue(fw._virtual_move)
            await fw.a_init()
            self.assertEqual(len(fw.positions), 0)
            # main method to make move
            start_time = time.time()
            self.assertTrue(fw.done)  # virtual moves is done before start
            await fw.run()
            self.assertTrue(time.time() - start_time < 0.5)  # method run() should make immediately
            await fw.wait()
            self.assertFalse(fw.error)  # finish witch no errors
            self.assertEqual(fw.progress, 1)
            self.assertTrue(fw.done)
            await self.tree_freezer.stop()

        asyncio.run(coro())
