import logging
import unittest

from ob.comunication.internal_client_api import InternalClientAPI
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.planrunner.ern.commands.command_Object import CommandObject
from ob.planrunner.ern.commands.command_Sequence import CommandSequence
from ob.planrunner.ern.plan_manager import PlanManager
from test.data_colection.base_async_test import BaseAsyncTest

logger = logging.getLogger(__name__.rsplit('.')[-1])


class TestPlanManager(unittest.TestCase, BaseAsyncTest):
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

        self.rm = self.loop.run_until_complete(self.tao.get_res_manager())
        self.pm = PlanManager(acs_res_mngr=self.rm, api=self.api_test,loop=self.loop)

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_from_dict(self):
        """Test method from_dict()"""
        var = {'command_name': 'SEQUENCE', 'subcommands': [
            {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351', 'V', '10'], 'kwargs': {'clamp': '5'}},
            {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351', 'V', '10'], 'kwargs': {'clamp': '5'}}
        ]
                }
        plan = self.pm.from_dict(dic=var,access_resource_manager=self.rm, api=self.api_test)
        self.assertIsInstance(plan, CommandSequence)
        self.assertEqual(len(plan.get_subcommands()), 2)
        for s in plan.get_subcommands():
            self.assertIsInstance(s, CommandObject)


if __name__ == '__main__':
    unittest.main()
