import logging
import unittest

from ob.planrunner.ern.commands.command_Object import CommandObject
from ob.planrunner.ern.commands.command_Sequence import CommandSequence
from ob.planrunner.ern.plan_manager import PlanManager
from test.data_colection.base_async_test import BaseAsyncTest

logger = logging.getLogger(__name__.rsplit('.')[-1])


class TestPlanManager(unittest.TestCase, BaseAsyncTest):

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.pm = PlanManager(loop=self.loop)  # can raise if not get or find loop

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_from_dict(self):
        """Test method from_dict()"""
        var = [{'command_name': 'SEQUENCE', 'all_commands': [
            {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351', 'V', '10'], 'kwargs': {'clamp': '5'}},
            {'command_name': 'OBJECT', 'args': ['NGC6871', '18.157', '-29.351', 'V', '10'], 'kwargs': {'clamp': '5'}}
        ]
                }]

        plan = self.pm.from_dict(var)
        self.assertIsInstance(plan, CommandSequence)
        self.assertEqual(len(plan.get_subcommands()), 2)
        for s in plan.get_subcommands():
            self.assertIsInstance(s, CommandObject)


if __name__ == '__main__':
    unittest.main()
