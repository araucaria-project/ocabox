import unittest
from datetime import datetime

from ob.data_colection.address import Address
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.ob_config import OBConfig


class ValueExchangeTest(unittest.TestCase):
    pass


class ValueRequestTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self._cfg = OBConfig()

    def tearDown(self) -> None:
        super().tearDown()

    def test_from_dict(self):
        """
        Test create ValueRequest class from dictionary.
        :return:
        """
        d = {'address': 'aaa.bbb.ccc', 'timestamp': datetime.now(), 'delta': 23, 'trash': 54}
        vr = ValueRequest.from_dict(d)
        self.assertTrue(hasattr(vr, 'address'))
        self.assertTrue(hasattr(vr, 'timestamp'))
        self.assertTrue(hasattr(vr, 'delta'))
        self.assertFalse(hasattr(vr, 'trash'))
        self.assertIsInstance(vr.address, Address)
        self.assertIsInstance(vr.timestamp, datetime)
        d = {'timestamp': datetime.now()}
        vr = ValueRequest.from_dict(d)

    def test_to_dict(self):
        expected_dict = {'address': {'adr': 'aaa.bbb.ccc'},
                         'timestamp': datetime(2022, 3, 15, 12, 40, 53).timestamp(), 'delta': 23}
        vr = ValueRequest(expected_dict['address'], datetime.fromtimestamp(expected_dict['timestamp']),
                          expected_dict['delta'])
        out_dict = vr.to_dict()
        self.assertNotIsInstance(out_dict['address'], Address, msg='Object Address has not implemented '
                                                                   'method to_dict()')
        self.assertDictEqual(out_dict, expected_dict)

    def test_default_config(self):
        expected_delta = self._cfg.config['ValueRequest']['delta'].get()
        vr = ValueRequest('aaa.bbb.ccc')
        # delta
        self.assertEqual(expected_delta, vr.delta)
        self.assertTrue(type(vr.delta) == int or float)
        # timestamp
        self.assertTrue(isinstance(vr.timestamp, datetime))


class ValueResponseTest(unittest.TestCase):
    def test_from_dict(self):
        """
        Test create ValueResponse class from dictionary.
        :return:
        """
        d = {'address': 'aaa.bbb.ccc', 'value': Value(234, datetime.now()), 'trash': 54}
        vr = ValueResponse.from_dict(d)
        self.assertTrue(hasattr(vr, 'address'))
        self.assertTrue(hasattr(vr, 'value'))
        self.assertFalse(hasattr(vr, 'trash'))
        self.assertIsInstance(vr.address, Address)
        self.assertIsInstance(vr.value, Value)

        value_dict = {'v': 234, 'ts': datetime(2022, 3, 15, 12, 40, 53), 'type': None, 'status': False, 'error': None}
        d = {'address': 'aaa.bbb.ccc', 'value': value_dict, 'trash': 54}
        vr = ValueResponse.from_dict(d)
        self.assertTrue(hasattr(vr, 'address'))
        self.assertTrue(hasattr(vr, 'value'))
        self.assertFalse(hasattr(vr, 'trash'))
        self.assertIsInstance(vr.address, Address)
        self.assertIsInstance(vr.value, Value)
        self.assertTrue(vr.value.v == value_dict['v'])
        self.assertTrue(vr.value.ts == value_dict['ts'])

    def test_to_dict(self):
        value_dict = {'v': 234, 'ts': datetime(2022, 3, 15, 12, 40, 53).timestamp(), 'type': None}
        expected_dict = {'address': {'adr': 'aaa.bbb.ccc'}, 'value': value_dict, 'status': False,
                         'error': {'code': 230, 'message': 'message error', 'component_name': 'sample_source',
                                   'severity': 'NORMAL'}}
        vr = ValueResponse(expected_dict['address'], Value(**value_dict), expected_dict['status'],
                           expected_dict['error'])
        out_dict = vr.to_dict()
        self.assertNotIsInstance(out_dict['address'], Address, msg='Object Address has not implemented '
                                                                   'method to_dict()')
        self.assertNotIsInstance(out_dict['value'], Value, msg='Object Value has not implemented '
                                                               'method to_dict()')
        self.assertNotIsInstance(out_dict['value']['ts'], datetime)
        self.assertDictEqual(out_dict, expected_dict)
        self.assertFalse(out_dict['status'])
        self.assertNotIsInstance(out_dict['error'], ResponseError, msg='Object ResponseError has not implemented '
                                                                       'method to_dict()')
        self.assertDictEqual(out_dict['error'], expected_dict['error'])


if __name__ == '__main__':
    unittest.main()
