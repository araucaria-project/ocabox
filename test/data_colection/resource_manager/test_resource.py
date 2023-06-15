import asyncio
import logging
import random
import time
import unittest

from pyaraucaria.coordinates import az_alt_2_ra_dec, ra_dec_epoch

from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.resource_manager.resource import DomeAlpaca, ResourceCommandError
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_base_request_blocker import TreeBaseRequestBlocker
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
        self.tao.target_requests = self.rs
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

    def test_Position_progress(self):
        """Test method `progress` from Position object"""

        async def coro():
            await self.tree_freezer.run()
            position_ra = random.randint(170, 190)
            rm = await self.tao.get_res_manager()
            dome = rm.get_resource(name=rm.DOME, nr=0)

            pos = dome.Position("abc", t=8.0, c="-1", s=int(-6))
            self.assertEqual(pos.progress, 5 / 14)

            pos = dome.Position("abc", t=True, c=False, s=False)
            self.assertEqual(pos.progress, 0)

            pos = dome.Position("abc", t=True, c=True, s=False)
            self.assertEqual(pos.progress, 1)

            pos = dome.Position("abc", t=1, c=1, s=None)
            self.assertEqual(pos.progress, 0)

            await self.tree_freezer.stop()

        asyncio.run(coro())

    def test_Move_progress(self):
        """Test method `progress` from Move object"""

        async def coro():
            await self.tree_freezer.run()
            position_ra = random.randint(170, 190)
            rm = await self.tao.get_res_manager()
            dome = rm.get_resource(name=rm.DOME, nr=0)

            mov = dome.Move(None)
            pos = dome.Position("abc", t=8.0, c="-1", s=int(-6))
            mov.positions.append(pos)
            pos2 = dome.Position("abc", t=7.0, c="6", s=int(-5))
            mov.positions.append(pos2)

            self.assertEqual(pos.progress, 5 / 14)
            self.assertEqual(pos2.progress, 11 / 12)

            self.assertEqual(mov.progress, (5 / 14 + 11 / 12) / 2)

            await self.tree_freezer.stop()

        asyncio.run(coro())


class DomeAlpacaTest(unittest.TestCase, BaseAsyncTest):
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


class MountAlpacaTest(unittest.TestCase, BaseAsyncTest):
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

    def test_go_to_position(self):
        """Test method `go_to_position`. WARNING, this test may not be performed correctly the first time due to the
        slow rotation of the dome on the simulator. In this case, the test should be repeated."""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            mount = rm.get_resource(name=rm.MOUNT, nr=0)
            position_ra, position_dec = az_alt_2_ra_dec(random.randint(30, 50), random.randint(20, 50),
                                                        mount._longitude, mount._latitude, mount._elevation)
            position_ra_final, position_dec_final = ra_dec_epoch(ra=position_ra,
                                                                 dec=position_dec,
                                                                 epoch=str("2000"))
            result = await mount.go_to_position(position_ra, position_dec, self.api_test)
            self.assertTrue(result)
            await mount.wait_for_slew()
            result = await self.api_test.get_async(f"{mount._tree_address_path.__str__()}.rightascension")
            self.assertTrue(position_ra_final - 0.5 < result.value.v < position_ra_final + 0.5)
            result = await self.api_test.get_async(f"{mount._tree_address_path.__str__()}.declination")
            self.assertTrue(position_dec_final - 0.5 < result.value.v < position_dec_final + 0.5)
            self.assertEqual(mount.get_slew_progres(), 1)
            await self.tree_freezer.stop()

        asyncio.run(coro())

    def test_custom_user_in_request(self):
        """Test method `go_to_position` when user is non defaulter API witch user with access.
        WARNING, this test may not be performed correctly the first time due to the
        slow rotation of the dome on the simulator. In this case, the test should be repeated."""
        blocker = TreeBaseRequestBlocker('block', self.tao)  # ad blocker to tree
        rs = RequestSolver(blocker)
        self.tao.target_requests = rs  # set new request solver
        api = InternalClientAPI(request_solver=rs, user_name=f"DefaultTest2")
        blocker.make_reservation(api.user, time.time() + 10)  # reserve client

        async def coro():
            await self.tree_freezer.run()
            # wrong user
            position_az = random.randint(170, 190)
            rm = await self.tao.get_res_manager()
            dome = rm.get_resource(name=rm.DOME, nr=0)
            with self.assertRaises(ResourceCommandError):
                result = await dome.go_to_position(alt=2, az=position_az, ra=None, dec=None)
            # correct user
            position_az = random.randint(170, 190)
            result = await dome.go_to_position(alt=2, az=position_az, ra=None, dec=None, api=api)
            await asyncio.sleep(2)  # Wait to reaction
            result = await self.api_test.get_async("dome.azimuth")
            self.assertEqual(position_az, result.value.v)
            await self.tree_freezer.stop()

        asyncio.run(coro())


if __name__ == '__main__':
    unittest.main()
