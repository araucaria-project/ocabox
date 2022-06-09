import asyncio
import datetime
import unittest

from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest
from test.data_colection.base_components.test_tree_base_provider import TreeBaseProviderTest


class TreeProviderTest(unittest.TestCase):
    SampleTestValueProvider = TreeBaseProviderTest.SampleTestValueProvider

    def setUp(self):
        super().setUp()
        self.v1 = ('val1', Value(1, datetime.datetime(2022, 5, 20, 1, 1, 1)))
        self.v2 = ('val2', Value(2, datetime.datetime(2022, 5, 20, 2, 2, 2)))
        self.vp1 = self.SampleTestValueProvider('provider1_name', [self.v1, self.v2])

        self.sample_address_prefix = 'aaa.bbb'
        self.start_index = len(self.sample_address_prefix.split('.')) - 1

    def tearDown(self) -> None:
        super().tearDown()

    def test_get_response_redirect_to_next(self):
        """
        test when get_value() method compels to call nex provider
        :return:
        """
        tbp = TreeProvider('component_sample_name', 'bbb', self.vp1)

        # test when is no next provider and get_value() method compels to call nex provider
        request = ValueRequest('.'.join([self.sample_address_prefix, self.v1[0]]), self.v1[1].ts.timestamp(), 20)
        request.index = self.start_index-1  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, self.v1[1])
        self.assertTrue(response.status)
        self.assertIsNone(response.error)


if __name__ == '__main__':
    unittest.main()
