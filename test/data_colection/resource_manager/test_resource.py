import asyncio
import logging
import random
import time
import unittest

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

            self.assertEqual(mov.progress, (5 / 14 + 11 / 12)/2)

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

    def test_go_to_position(self):
        """Test method `go_to_position`. WARNING, this test may not be performed correctly the first time due to the
        slow rotation of the dome on the simulator. In this case, the test should be repeated."""

        async def coro():
            await self.tree_freezer.run()
            position_az = random.randint(170, 190)
            rm = await self.tao.get_res_manager()
            dome = rm.get_resource(name=rm.DOME, nr=0)
            result = await dome.go_to_position(2, position_az, None, None)
            self.assertTrue(result)
            await asyncio.sleep(2)  # Wait to reaction
            result = await self.api_test.get_async("dome.azimuth")
            self.assertEqual(position_az, result.value.v)
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

    def test_wait_to_slew(self):
        """Test method `wait_to_slew` WARNING, this test may not be performed correctly the first time due to the
        slow rotation of the dome on the simulator. In this case, the test should be repeated."""

        async def coro():
            await self.tree_freezer.run()
            position_az = random.randint(170, 190)
            rm = await self.tao.get_res_manager()
            dome = rm.get_resource(name=rm.DOME, nr=0)

            t = asyncio.create_task(dome.wait_to_slew(2, position_az, None, None, timeout=7))
            await asyncio.sleep(0.1)  # wait for task start
            self.assertFalse(t.done())

            # move dome to position
            result = await dome.go_to_position(2, position_az, None, None)
            self.assertTrue(result)
            # await asyncio.sleep(2)  # Wait to reaction
            # result = await self.api_test.get_async("dome.azimuth", time_of_data_tolerance=0)
            # self.assertEqual(position_az, result.value.v)
            # wait for finish
            await t
            self.assertTrue(t.done())
            await self.tree_freezer.stop()

        asyncio.run(coro())


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
            position_ra = random.randint(70, 90)
            position_dec = random.randint(70, 90)
            rm = await self.tao.get_res_manager()
            mount = rm.get_resource(name=rm.MOUNT, nr=0)
            result = await mount.go_to_position(position_ra, position_dec, '2000', self.api_test)
            print("----", mount.get_slew_progres())
            await asyncio.sleep(1.5)
            print("----", mount.get_slew_progres())
            await asyncio.sleep(0.5)
            print("----", mount.get_slew_progres())
            await asyncio.sleep(5.5)
            print("----", mount.get_slew_progres())
            self.assertTrue(result)
            # await asyncio.sleep(2)  # Wait to reaction
            # result = await self.api_test.get_async("dome.azimuth")
            # self.assertEqual(position_az, result.value.v)
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

    def test_wait_to_slew(self):
        """Test method `wait_to_slew` WARNING, this test may not be performed correctly the first time due to the
        slow rotation of the dome on the simulator. In this case, the test should be repeated."""

        async def coro():
            await self.tree_freezer.run()
            position_az = random.randint(170, 190)
            rm = await self.tao.get_res_manager()
            dome = rm.get_resource(name=rm.DOME, nr=0)

            t = asyncio.create_task(dome.wait_to_slew(2, position_az, None, None, timeout=7))
            await asyncio.sleep(0.1)  # wait for task start
            self.assertFalse(t.done())

            # move dome to position
            result = await dome.go_to_position(2, position_az, None, None)
            self.assertTrue(result)
            # await asyncio.sleep(2)  # Wait to reaction
            # result = await self.api_test.get_async("dome.azimuth", time_of_data_tolerance=0)
            # self.assertEqual(position_az, result.value.v)
            # wait for finish
            await t
            self.assertTrue(t.done())
            await self.tree_freezer.stop()

        asyncio.run(coro())


if __name__ == '__main__':
    unittest.main()
