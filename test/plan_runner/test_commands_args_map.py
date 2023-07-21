import unittest

from ob.planrunner.ern.commands.commands_args_map import CommandArgsMap


class TestCommandArgsMap(unittest.TestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_in_operator_overload(self):
        self.assertTrue(CommandArgsMap.TRACKING.get_item("on").val())
        self.assertTrue(CommandArgsMap.TRACKING.has_item("on"))
        self.assertFalse(CommandArgsMap.TRACKING.has_item("on_1111"))
        self.assertTrue(CommandArgsMap.TRACKING.ON.val())
        self.assertFalse(CommandArgsMap.TRACKING.OFF.val())


if __name__ == '__main__':
    unittest.main()
