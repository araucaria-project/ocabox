import datetime
import unittest
from typing import List, Tuple

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_base_broker import TreeBaseBroker
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse


class TreeBaseBrokerTest(unittest.TestCase):

    class SampleTestValueProvider(TreeProvider):

        def get_value(self, request: ValueRequest) -> Value or None:
            address = request.address
            value_name = address[address.get_last_index()]
            for n, v in self.test_values:
                if value_name == n:
                    return v
            return None

        def __init__(self, component_name: str, source_name: str, test_values: List[Tuple[str, Value]],
                     subcontractor: ProvidesResponseProtocol = None, **kwargs):
            self.test_values: List[Tuple[str, Value]] = test_values
            super().__init__(component_name=component_name, subcontractor=subcontractor, source_name=source_name,
                             **kwargs)

    def setUp(self):
        super().setUp()
        self.v1 = ('val1', Value(1, datetime.datetime(2022, 5, 20, 1, 1, 1)))
        self.v2 = ('val2', Value(2, datetime.datetime(2022, 5, 20, 2, 2, 2)))
        self.v3 = ('val3', Value(3, datetime.datetime(2022, 5, 20, 3, 3, 3)))
        self.v4 = ('val4', Value(4, datetime.datetime(2022, 5, 20, 4, 4, 4)))

        self.vp1 = self.SampleTestValueProvider('provider1_name', 'provider1', [self.v1, self.v2])
        self.vp2 = self.SampleTestValueProvider('provider2_name', 'provider2', [self.v3, self.v4])

    def tearDown(self) -> None:
        super().tearDown()

    def test_init(self):
        """
        Test correct initialize object
        :return:
        """
        vb = TreeBaseBroker('DefaultBroker')
        self.assertIsInstance(vb.get_list_providers(), list)
        self.assertTrue(vb.get_list_providers() == [])

    def test_get_provider(self):
        """
        Test provider from broker.
        :return:
        """
        vb = TreeBaseBroker('DefaultBroker', [self.vp1, self.vp2])
        # good provider
        request = ValueRequest('.'.join([self.vp1.get_source_name(), self.v1[0]]), self.v1[1].ts.timestamp(), 20)
        provider = vb._get_provider(request)
        self.assertEqual(provider.get_source_name(), self.vp1.get_source_name())
        self.assertIs(provider, self.vp1)
        # nonexistent provider
        request = ValueRequest('.'.join(['nonexistent_provider', self.v1[0]]), self.v1[1].ts.timestamp(), 20)
        provider = vb._get_provider(request)
        self.assertIsNone(provider)
        # wrong address
        request = ValueRequest('.'.join(['']), self.v1[1].ts.timestamp(), 20)
        self.assertRaises(AddressError, vb._get_provider, request)

    def test_add_provider(self):
        """
        Test add provider.
        :return:
        """
        vb = TreeBaseBroker('DefaultBroker', [self.vp1])
        # correct added new provider
        effect = vb.add_provider(self.vp2)
        self.assertTrue(effect)
        self.assertEqual(vb.get_list_providers(), [self.vp1, self.vp2])
        # try add again the same provider
        effect = vb.add_provider(self.vp2)
        self.assertFalse(effect)
        self.assertEqual(vb.get_list_providers(), [self.vp1, self.vp2])
        # try force add again the same provider - broker should remove old provider and add new
        effect = vb.add_provider(self.vp1, True)
        self.assertTrue(effect)
        self.assertEqual(vb.get_list_providers(), [self.vp2, self.vp1])

    def test_get_response(self):
        """
        Test get response from broker.
        :return:
        """
        vb = TreeBaseBroker('DefaultBroker', [self.vp1, self.vp2])
        # good request
        request = ValueRequest('.'.join([self.vp1.get_source_name(), self.v1[0]]), self.v1[1].ts.timestamp(), 20)
        response = vb.get_response(request)
        self.assertTrue(response.status)
        self.assertEqual(response.value, self.v1[1])
        # wrong request - provider not exist
        request = ValueRequest('.'.join(['nonexistent_provider', self.v1[0]]), self.v1[1].ts.timestamp(), 20)
        response = vb.get_response(request)
        self.assertEqual(response.address, request.address)
        self.assertIsNone(response.value)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, 1002)


if __name__ == '__main__':
    unittest.main()
