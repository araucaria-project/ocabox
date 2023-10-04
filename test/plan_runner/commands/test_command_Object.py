import asyncio
import random
import unittest

from pyaraucaria.coordinates import az_alt_2_ra_dec, ra_dec_epoch

from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.planrunner.ern.commands.command_Object import CommandObject
from ob.planrunner.ern.errors import PlanBuildError
from ob.planrunner.ern.moves.move import Move
from ob.planrunner.ern.moves.position import Position
from ob.planrunner.ern.plan_manager import PlanManager
from test.data_colection.base_async_test import BaseAsyncTest


class CommandObjectTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.tree_cache = TreeCache('sample_name_cache', self.tao)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.rs = RequestSolver(self.tree_freezer)
        self.api_test = InternalClientAPI(request_solver=self.rs, user_name=f"DefaultTest")

        self.rm = self.loop.run_until_complete(self.tao.get_res_manager())
        self.pm = PlanManager(acs_res_mngr=self.rm, api=self.api_test, loop=self.loop)

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_build_command_object(self):
        """Test build command Object witch validate arguments"""
        # ------------------------ positive ------------------------
        var = {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351'], 'kwargs': {'clamp': '5'}}
        plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
        self.assertIsInstance(plan, CommandObject)

        # -------------------- validate args --------------------
        var = {'command_name': 'OBJECT', 'args': ['NGC6871'], 'kwargs': {'clamp': '5'}}
        plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
        self.assertIsInstance(plan, CommandObject)
        # ----------------------------------------
        var = {'command_name': 'OBJECT', 'args': ['18.157', '-29.351'], 'kwargs': {'clamp': '5'}}
        with self.assertRaises(PlanBuildError):
            plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
        # ----------------------------------------
        var = {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157'], 'kwargs': {'clamp': '5'}}
        with self.assertRaises(PlanBuildError):
            plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)

        # -------------------- dither param --------------------
        # wrong dither param
        var = {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351'], 'kwargs': {'dither': '5'}}
        with self.assertRaises(PlanBuildError):
            plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
        self.assertFalse(plan.dither_on)
        # good dither param
        var = {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351'], 'kwargs': {"seq": "2/v/1",
                                                                                              'dither': 'base/2/3'}}
        plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
        self.assertIsInstance(plan, CommandObject)
        self.assertTrue(plan.dither_on)
        # turn off dither
        var = {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351'], 'kwargs': {'dither': 'none'}}
        plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
        self.assertIsInstance(plan, CommandObject)
        self.assertFalse(plan.dither_on)
        # ----
        var = {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351'], 'kwargs': {"seq": "4/v/1",
                                                                                              'dither': 'base/2/3'}}
        plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
        self.assertIsInstance(plan, CommandObject)
        self.assertFalse(plan._execute_seq_subcomands[0].exp_list[0][3]._virtual_move)
        self.assertTrue(plan._execute_seq_subcomands[0].exp_list[0][3].dither_frequency_nr == 0)
        self.assertTrue(plan._execute_seq_subcomands[0].exp_list[0][3].dither_distance == 3)
        self.assertTrue(plan._execute_seq_subcomands[0].exp_list[1][3]._virtual_move)

    def test_run_command_object(self):
        """Test run command Object"""
        mount = self.rm.get_resource(name=self.rm.MOUNT, nr=0)
        dome = self.rm.get_resource(name=self.rm.DOME, nr=0)
        az = random.randint(30, 50)
        alt = random.randint(20, 50)
        position_ra, position_dec = az_alt_2_ra_dec(az, alt,
                                                    mount.longitude, mount.latitude, mount.elevation)
        position_ra_final, position_dec_final = ra_dec_epoch(ra=position_ra,
                                                             dec=position_dec,
                                                             epoch=str("2000"))

        # todo w tym teście jest zapisywane zdjęcie więc jak będzie nowy mechanizm to dorobić jakieś usuwanie
        #  tego zdjęcia

        async def coro():
            await self.rs.run_tree()
            names = (await self.api_test.get_async(f"{self.rm.get_resource(self.rm.FILTERWHEEL).adr}.names")).value.v
            targ_filter = names[random.randint(0, len(names) - 1)]

            filter_ = targ_filter
            number_of_photo = 1
            var = {'command_name': 'OBJECT', 'args': ['NGC6871', position_ra, position_dec],
                   'kwargs': {'clamp': '5', "seq": f"{number_of_photo}/{filter_}/1"}}

            plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
            await plan.a_init()

            self.assertIsInstance(plan, CommandObject)
            self.assertEqual(plan._execute_seq_subcomands[0].filter._filter, filter_)  # right filter
            self.assertFalse(plan._execute_seq_subcomands[0].filter._virtual_move)
            focuserFocus, cameraExposure, cameraReadPicture, mountDither = plan._execute_seq_subcomands[0].exp_list[0]
            self.assertTrue(focuserFocus._virtual_move)  # skip focusing
            self.assertTrue(mountDither._virtual_move)  # skip dithering
            self.assertEqual(len(plan._execute_seq_subcomands[0].exp_list), number_of_photo)

            await plan.run()

            # --------------------------------- check some status is correct ---------------
            result = await self.api_test.get_async(f"{mount.adr}.rightascension")
            self.assertTrue(position_ra_final - 0.5 < result.value.v < position_ra_final + 0.5)
            result = await self.api_test.get_async(f"{mount.adr}.declination")
            self.assertTrue(position_dec_final - 0.5 < result.value.v < position_dec_final + 0.5)

            result = await self.api_test.get_async(f"{dome.adr}.azimuth")
            self.assertTrue(az - 0.5 < result.value.v < az + 0.5)
            await self.rs.stop_tree()
            await asyncio.sleep(1)

        asyncio.run(coro())

    def test_cancel_positions_when_error(self):
        """the test checks whether all 'positions' are canceled when the command got error."""
        mount = self.rm.get_resource(name=self.rm.MOUNT, nr=0)
        dome = self.rm.get_resource(name=self.rm.DOME, nr=0)
        az = random.randint(30, 50)
        alt = random.randint(20, 50)
        position_ra, position_dec = az_alt_2_ra_dec(az, alt,
                                                    mount.longitude, mount.latitude, mount.elevation)
        position_ra_final, position_dec_final = ra_dec_epoch(ra=position_ra,
                                                             dec=position_dec,
                                                             epoch=str("2000"))

        async def coro():
            await self.rs.run_tree()
            names = (await self.api_test.get_async(f"{self.rm.get_resource(self.rm.FILTERWHEEL).adr}.names")).value.v
            targ_filter = names[random.randint(0, len(names) - 1)]

            filter_ = targ_filter
            number_of_photo = 1
            var = {'command_name': 'OBJECT', 'args': ['NGC6871', position_ra, position_dec],
                   'kwargs': {'clamp': '5', "seq": f"{number_of_photo}/{filter_}/1"}}

            plan = self.pm.from_dict(dic=var, access_resource_manager=self.rm, api=self.api_test)
            await plan.a_init()

            # change mount and dome Move targets to impossible values
            self.assertIsInstance(plan, CommandObject)
            plan._move_dome.positions[0].target = 1000  # set target impossible to get
            plan._move_dome._position_az_name = "notexsistingname"  # change the name because target
            # position is updating after start and is getting by name. We not want to change
            plan._move_mount.positions[0].target = 1000  # set target impossible to get

            self.assertIsInstance(plan, CommandObject)

            task_run = asyncio.create_task(plan.run())  # run command
            await asyncio.sleep(0.5)  # wait to start
            task_run.cancel()  # cancel task
            await asyncio.sleep(0.5)
            # -------- check positions is canceled too --------
            self.assertTrue(plan._move_mount.positions[0].done())
            self.assertTrue(plan._move_mount.positions[0].task.cancelled())
            self.assertTrue(plan._move_dome.positions[0].done())
            self.assertTrue(plan._move_dome.positions[0].task.cancelled())
            await self.rs.stop_tree()
            await asyncio.sleep(1)

        asyncio.run(coro())


if __name__ == '__main__':
    unittest.main()
