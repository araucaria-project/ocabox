import unittest
from datetime import datetime, timedelta

from ob.data_colection.address import Address
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse


class ValueExchangeTest(unittest.TestCase):
    pass


class ValueRequestTest(unittest.TestCase):

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

    def test_to_dict(self):
        expected_dict = {'address': {'adr': 'aaa.bbb.ccc'},
                         'timestamp': datetime(2022, 3, 15, 12, 40, 53).timestamp(), 'delta': 23}
        vr = ValueRequest(expected_dict['address'], datetime.fromtimestamp(expected_dict['timestamp']),
                          expected_dict['delta'])
        out_dict = vr.to_dict()
        self.assertNotIsInstance(out_dict['address'], Address, msg='Object Address has not implemented '
                                                                   'method to_dict()')
        self.assertDictEqual(out_dict, expected_dict)


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

        value_dict = {'v': 234, 'ts': datetime(2022, 3, 15, 12, 40, 53), 'type': None}
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
        expected_dict = {'address': {'adr': 'aaa.bbb.ccc'}, 'value': value_dict}
        vr = ValueResponse(expected_dict['address'], Value(**value_dict))
        out_dict = vr.to_dict()
        self.assertNotIsInstance(out_dict['address'], Address, msg='Object Address has not implemented '
                                                                   'method to_dict()')
        self.assertNotIsInstance(out_dict['value'], Value, msg='Object Value has not implemented '
                                                               'method to_dict()')
        self.assertNotIsInstance(out_dict['value']['ts'], datetime)
        self.assertDictEqual(out_dict, expected_dict)


if __name__ == '__main__':
    unittest.main()
