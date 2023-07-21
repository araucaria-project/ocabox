import asyncio
import random
import time
import unittest

from pyaraucaria.coordinates import az_alt_2_ra_dec

from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.planrunner.ern.errors import PlanBuildError
from ob.planrunner.ern.moves.custom_moves.dome_slew import DomeSlew
from ob.planrunner.ern.moves.custom_moves.dome_slew_ra_dec import DomeSlewRaDec
from ob.planrunner.ern.plan_data import PlanData
from test.data_colection.base_async_test import BaseAsyncTest


class DomeSlewRaDecTest(unittest.TestCase, BaseAsyncTest):
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

    def test_go_to_position_ra_dec(self):
        """Test slew dome to position az"""

        async def coro():
            try:
                await self.tree_freezer.run()
                rm = await self.tao.get_res_manager()
                plan_data = PlanData(access_resource_manager=rm, client_api=self.api_test)
                dome = rm.get_resource(name=rm.DOME, nr=0)
                mount = rm.get_resource(name=rm.MOUNT, nr=0)
                az = random.randint(30, 50)
                alt = random.randint(20, 50)
                position_ra, position_dec = az_alt_2_ra_dec(az, alt,
                                                            mount.longitude, mount.latitude, mount.elevation)

                fw = DomeSlewRaDec(ra_dec=(position_ra, position_dec), plan_data=plan_data)
                await fw.a_init()
                start_time = time.time()
                await fw.run()
                self.assertTrue(time.time() - start_time < 0.5)  # method run() should make immediately
                await fw.wait()
                self.assertFalse(fw.error)  # finish witch no errors
                result = await self.api_test.get_async(f"{dome.adr}.azimuth")
                self.assertTrue(az - 0.5 < result.value.v < az + 0.5)
                self.assertEqual(fw.progress, 1)
            finally:
                await self.tree_freezer.stop()

        asyncio.run(coro())
    #
    # def test_go_to_position_wrong_params(self):
    #     """Test slew mount to position wrong position format"""
    #
    #     async def coro():
    #         try:
    #             await self.tree_freezer.run()
    #             rm = await self.tao.get_res_manager()
    #             plan_data = PlanData(access_resource_manager=rm, client_api=self.api_test)
    #             position_alt = random.randint(30, 50)
    #             with self.assertRaises(PlanBuildError):
    #                 fw = DomeSlewRaDec(az=None, plan_data=plan_data)
    #         finally:
    #             await self.tree_freezer.stop()
    #
    #     asyncio.run(coro())
