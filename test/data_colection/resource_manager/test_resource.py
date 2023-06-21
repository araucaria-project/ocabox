import asyncio
import logging
import random
import unittest
from pyaraucaria.coordinates import az_alt_2_ra_dec, ra_dec_epoch
from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.data_colection.resource_manager.resource import DomeAlpaca
from ob.data_colection.resource_manager.moves.move import Move
from ob.data_colection.resource_manager.moves.position import Position
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

            pos = Position("abc", t=8.0, c="-1", s=int(-6))
            self.assertEqual(pos.progress, 5 / 14)

            pos = Position("abc", t=True, c=False, s=False)
            self.assertEqual(pos.progress, 0)

            pos = Position("abc", t=True, c=True, s=False)
            self.assertEqual(pos.progress, 1)

            pos = Position("abc", t=1, c=1, s=None)
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

            mov = Move(None)
            pos = Position("abc", t=8.0, c="-1", s=int(-6))
            mov.positions.append(pos)
            pos2 = Position("abc", t=7.0, c="6", s=int(-5))
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

    def test_go_to_position_ra_dec(self):
        """Test slew mount to position ra dec"""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            mount = rm.get_resource(name=rm.MOUNT, nr=0)
            position_ra, position_dec = az_alt_2_ra_dec(random.randint(30, 50), random.randint(20, 50),
                                                        mount.longitude, mount.latitude, mount.elevation)
            position_ra_final, position_dec_final = ra_dec_epoch(ra=position_ra,
                                                                 dec=position_dec,
                                                                 epoch=str("2000"))
            m = mount.build_go_to_position(ra=position_ra, dec=position_dec, alt=None, az=None, api=self.api_test)
            await m.make()
            await m.wait()
            result = await self.api_test.get_async(f"{mount.adr}.rightascension")
            self.assertTrue(position_ra_final - 0.5 < result.value.v < position_ra_final + 0.5)
            result = await self.api_test.get_async(f"{mount.adr}.declination")
            self.assertTrue(position_dec_final - 0.5 < result.value.v < position_dec_final + 0.5)
            self.assertEqual(m.progress, 1)
            await self.tree_freezer.stop()

        asyncio.run(coro())

    def test_go_to_position_alt_az(self):
        """Test slew mount to position alt az"""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            mount = rm.get_resource(name=rm.MOUNT, nr=0)
            position_alt = random.randint(30, 50)
            position_az = random.randint(30, 50)
            m = mount.build_go_to_position(ra=None, dec=None, alt=position_alt, az=position_az, api=self.api_test)
            await m.make()
            await m.wait()
            result = await self.api_test.get_async(f"{mount.adr}.altitude")
            self.assertTrue(position_alt - 0.5 < result.value.v < position_alt + 0.5)
            result = await self.api_test.get_async(f"{mount.adr}.azimuth")
            self.assertTrue(position_az - 0.5 < result.value.v < position_az + 0.5)
            self.assertEqual(m.progress, 1)
            await self.tree_freezer.stop()

        asyncio.run(coro())

    def test_go_to_position_wrong_params(self):
        """Test slew mount to position wrong position format"""

        async def coro():
            await self.tree_freezer.run()
            rm = await self.tao.get_res_manager()
            mount = rm.get_resource(name=rm.MOUNT, nr=0)
            m = mount.build_go_to_position(ra=random.randint(30, 50), dec=None, alt=None, az=random.randint(30, 50),
                                           api=self.api_test)
            with self.assertRaises(ResourceCommandError):
                await m.make()
            await self.tree_freezer.stop()

        asyncio.run(coro())


if __name__ == '__main__':
    unittest.main()
