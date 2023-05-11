import logging
import unittest
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from test.data_colection.base_async_test import BaseAsyncTest

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ResourceManagerTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)
        self.rm = None

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_(self):
        self.assertTrue(True)


class ResourceManagerAlpacaTest(unittest.TestCase, BaseAsyncTest):
    OBSERVATORY_NAME = 'test_observatory'

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory(component_name='sample_component', observatory_name=self.OBSERVATORY_NAME)

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_(self):
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
