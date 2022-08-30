import asyncio
import unittest
from typing import List, Tuple

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_base_provider import TreeBaseProvider
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.value import Value, TreeValueError
from ob.data_colection.value_call import ValueRequest


class TreeBaseProviderTest(unittest.TestCase):
    class SampleTestValueProvider(TreeBaseProvider):

        async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
            address = request.address
            value_name = address[address.get_last_index()]
            for n, v in self.test_values:
                if value_name == n:
                    return v
            if value_name == 'address_error_coded':
                raise AddressError(request.address, 20, '')
            if value_name == 'address_error':
                raise AddressError
            if value_name == 'value_error_coded':
                raise TreeValueError(None, 10, '')
            if value_name == 'value_error':
                raise TreeValueError
            if value_name == 'wrong_type':
                return 34
            if value_name == 'crash':
                raise ValueError
            return None

        def __init__(self, component_name: str, test_values: List[Tuple[str, Value]],
                     subcontractor: ProvidesResponseProtocol = None, **kwargs):
            self.test_values: List[Tuple[str, Value]] = test_values
            super().__init__(component_name=component_name, subcontractor=subcontractor, **kwargs)

    def setUp(self):
        super().setUp()
        self.v1 = ('val1', Value(1, 1661349399.030824))
        self.v2 = ('val2', Value(2, 1661349399.030824))
        self.vp1 = self.SampleTestValueProvider('provider1_name', [self.v1, self.v2])

        self.sample_address_prefix = 'aaa.bbb'
        self.start_index = len(self.sample_address_prefix.split('.')) - 1

    def tearDown(self) -> None:
        super().tearDown()

    def test_get_response_redirect_to_next(self):
        """
        test when get_value() method compels to call next provider
        :return:
        """
        tbp = TreeBaseProvider('component_sample_name', self.vp1)

        request = ValueRequest('.'.join([self.sample_address_prefix, self.v1[0]]), self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, self.v1[1])
        self.assertTrue(response.status)
        self.assertIsNone(response.error)

    def test_get_response_no_next_component(self):
        """
        test when is no next provider and get_value() method compels to call next provider
        :return:
        """
        tbp = TreeBaseProvider('component_sample_name', None)
        request = ValueRequest('.'.join([self.sample_address_prefix, self.v1[0]]), self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, 3001)

    def test_get_response_address_error(self):
        """
        test when get_value() method call AddressError
        :return:
        """
        tbp = self.vp1
        # without specific code
        request = ValueRequest('.'.join([self.sample_address_prefix, 'address_error']), self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, AddressError.CODE_GROUP)  # code CODE_GROUP means no code was specified

        # with specific code
        request = ValueRequest('.'.join([self.sample_address_prefix, 'address_error_coded']),
                               self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, 20)

    def test_get_response_value_error(self):
        """
        test when get_value() method call TreeValueError
        :return:
        """
        tbp = self.vp1
        # without specific code
        request = ValueRequest('.'.join([self.sample_address_prefix, 'value_error']), self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, TreeValueError.CODE_GROUP)  # code CODE_GROUP means no code was specified

        # with specific code
        request = ValueRequest('.'.join([self.sample_address_prefix, 'value_error_coded']),
                               self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, 10)

    def test_get_response_wrong_type(self):
        """
        test when get_value() method return wrong type
        :return:
        """
        tbp = self.vp1
        request = ValueRequest('.'.join([self.sample_address_prefix, 'wrong_type']), self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        response = asyncio.run(tbp.get_response(request))
        self.assertEqual(response.value, None)
        self.assertFalse(response.status)
        self.assertEqual(response.error.code, 2002)

    def test_get_response_crash(self):
        """
        test when get_value() method raise not supported error
        :return:
        """
        tbp = self.vp1
        request = ValueRequest('.'.join([self.sample_address_prefix, 'crash']), self.v1[1].ts, 20)
        request.index = self.start_index  # set manually index
        self.assertRaises(ValueError, asyncio.run, tbp.get_response(request))


if __name__ == '__main__':
    unittest.main()
