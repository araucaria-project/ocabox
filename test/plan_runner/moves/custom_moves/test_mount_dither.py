import asyncio
import time
import unittest
from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.planrunner.ern.dither_data import DitherModes
from ob.planrunner.ern.moves.custom_moves.mount_dither import MountDither, DitherShareStartPosition
from ob.planrunner.ern.plan_data import PlanData
from test.data_colection.base_async_test import BaseAsyncTest


class MountDitherTest(unittest.TestCase, BaseAsyncTest):
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

    def test_dither(self):
        """Test dither"""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            plan_data = PlanData(access_resource_manager=rm, client_api=self.api_test)
            mount = rm.get_resource(name=rm.MOUNT, nr=0)

            # set tracking
            result = await self.api_test.put_async(f"{mount.adr}.tracking", parameters_dict={"Tracking": True},
                                                   no_wait=False)
            self.assertIsNone(result.error)
            ra_start = (await self.api_test.get_async(f"{mount.adr}.rightascension", time_of_data_tolerance=0)).value.v
            dec_start = (await self.api_test.get_async(f"{mount.adr}.declination", time_of_data_tolerance=0)).value.v
            dither_distance = 30

            sharing_date_between_dithering = DitherShareStartPosition()
            fw = MountDither(dither_mode=DitherModes.BASIC,
                             dither_distance=dither_distance,
                             plan_data=plan_data,
                             resource_nr=0,
                             dither_share_start_position=sharing_date_between_dithering,
                             virtual_move=False)
            await fw.a_init()
            self.assertIsNone(fw.positions[0].target)  # target is updating after run
            start_time = time.time()
            await fw.run()
            self.assertIsNotNone(fw.positions[0].target)
            self.assertTrue(time.time() - start_time < 0.5)  # method run() should make immediately
            await fw.wait()
            self.assertFalse(fw.error)  # finish witch no errors
            result = await self.api_test.get_async(f"{mount.adr}.rightascension", time_of_data_tolerance=0)
            self.assertNotEqual(ra_start, result.value.v)
            result = await self.api_test.get_async(f"{mount.adr}.declination", time_of_data_tolerance=0)
            self.assertNotEqual(dec_start, result.value.v)
            self.assertEqual(fw.progress, 1)
            await self.tree_freezer.stop()

        asyncio.run(coro())
