import unittest

from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest
from test.data_colection.base_async_test import BaseAsyncTest
from test.data_colection.sample_test_value_provider import SampleTestValueProvider


class TreeProviderTest(unittest.TestCase, BaseAsyncTest):

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.v1 = ('val1', Value(1, 1661349399.030824))
        self.v2 = ('val2', Value(2, 1661349399.030824))
        self.vp1 = SampleTestValueProvider('provider1_name', 'provider1_source_name', [self.v1, self.v2])

        self.sample_address_prefix = 'aaa.bbb'
        self.start_index = len(self.sample_address_prefix.split('.'))

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_get_response_redirect_to_next(self):
        """
        test when get_value() method compels to call nex provider
        :return:
        """
        name = 'name'
        tp = TreeProvider('component_sample_name', name, self.vp1)

        request = ValueRequest('.'.join([self.sample_address_prefix, name, self.vp1.get_source_name(), self.v1[0]]),
                               self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = self.loop.run_until_complete(tp.get_response(request))
        self.assertEqual(response.value, self.v1[1])
        self.assertTrue(response.status)
        self.assertIsNone(response.error)

    def test_get_response_to_short_address(self):
        """This test checks for an index error when passing a query between providers. The test checks if the address
        is too short and the index will be moved further, if the last provider will have a problem with 'out of range'.
        It shouldn't have happened"""
        tp3 = TreeProvider('component_sample_name3', 'ccc', None)
        tp2 = TreeProvider('component_sample_name2', 'bbb', tp3)
        tp1 = TreeProvider('component_sample_name1', 'aaa', tp2)

        async def coro():
            req = ValueRequest('aaa.bbb')
            result = await tp1.get_response(req)
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.error)
            self.assertTrue(result.error.code == 2002)
        self.loop.run_until_complete(coro())

    def test_get_response_wrong_address_in_line(self):
        """This test checks for correct operation of stopping request forwarding in case of a bad address between
        two providers."""
        tp3 = TreeProvider('component_sample_name3', 'ccc', None)
        tp2 = TreeProvider('component_sample_name2', 'bbb', tp3)
        tp1 = TreeProvider('component_sample_name1', 'aaa', tp2)

        async def coro():
            req = ValueRequest('aaa.ddd.ccc')
            result = await tp1.get_response(req)
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.error)
            self.assertTrue(result.error.code == 1002)
            self.assertIsNone(result.value)
        self.loop.run_until_complete(coro())

    def test_get_resource(self):
        """Test method get_resources"""
        name = 'name'
        tp = TreeProvider('component_sample_name', name, self.vp1)
        resources = tp.get_resources()
        self.assertEqual(("component_sample_name_RESOURCE", [name]), resources[0])


if __name__ == '__main__':
    unittest.main()
