import asyncio
import time
import unittest
from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.resource_manager.resource import CovercalibratorAlpaca
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.planrunner.ern.moves.custom_moves.mirror_cover_cls_opn import MirrorCoverClsOpn
from ob.planrunner.ern.plan_data import PlanData
from test.data_colection.base_async_test import BaseAsyncTest


class MirrorCoverClsOpnTest(unittest.TestCase, BaseAsyncTest):
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

    def test_open_close_cover(self):
        """Test set filter"""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            plan_data = PlanData(access_resource_manager=rm, client_api=self.api_test)
            # --------------- Open ---------------
            fw = MirrorCoverClsOpn(action=True, plan_data=plan_data)
            await fw.a_init()
            # main method to make move
            start_time = time.time()
            await fw.run()
            self.assertTrue(time.time() - start_time < 0.5)  # method run() should make immediately
            await fw.wait()
            self.assertFalse(fw.error)  # finish witch no errors
            result = await self.api_test.get_async(f"{rm.get_resource(rm.COVERCALIBRATOR).adr}.coverstate")
            self.assertEqual(result.value.v, CovercalibratorAlpaca.COVER_STATUS_MAP.get("open"))
            self.assertEqual(fw.progress, 1)

            # --------------- Close ---------------
            fw = MirrorCoverClsOpn(action=False, plan_data=plan_data)
            await fw.a_init()
            # main method to make move
            start_time = time.time()
            await fw.run()
            self.assertTrue(time.time() - start_time < 0.5)  # method run() should make immediately
            await fw.wait()
            self.assertFalse(fw.error)  # finish witch no errors
            result = await self.api_test.get_async(f"{rm.get_resource(rm.COVERCALIBRATOR).adr}.coverstate")
            self.assertEqual(result.value.v, CovercalibratorAlpaca.COVER_STATUS_MAP.get("closed"))
            self.assertEqual(fw.progress, 1)

            await self.tree_freezer.stop()

        asyncio.run(coro())
