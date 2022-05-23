import unittest
from datetime import datetime, timedelta

from ob.data_colection.value import Value


class ValueTest(unittest.TestCase):

    def test_value_eq(self):
        """
        Test equal two Address objects.
        :return:
        """
        now = datetime.now()
        a1 = Value(15, now)
        later = datetime.now()
        a2 = Value(15, later)
        self.assertEqual(a1, a2)
        later = datetime.now()
        a2 = Value(16, later)
        self.assertNotEqual(a1, a2)

    def test_value_gt(self):
        now = datetime.now()
        a1 = Value(15, now)
        later = datetime.now()
        a2 = Value(14, later)
        self.assertGreater(a1, a2)
        later = datetime.now()
        a2 = Value(16, later)
        self.assertGreater(a2, a1)

    def test_value_lt(self):
        now = datetime.now()
        a1 = Value(15, now)
        later = datetime.now()
        a2 = Value(16, later)
        self.assertLess(a1, a2)
        later = datetime.now()
        a2 = Value(14, later)
        self.assertLess(a2, a1)

    def test_date_expired(self):

        now = datetime(2022, 5, 15, 12, 54, 43)
        v_date = datetime(2022, 5, 15, 12, 52, 43)  # two minutes older then now
        v1 = Value(23, v_date)
        self.assertTrue(v1.is_expired(now))
        delta = timedelta(minutes=3)
        self.assertFalse(v1.is_expired(now, delta))
        past = datetime(2022, 5, 15, 12, 51, 43)
        self.assertFalse(v1.is_expired(past))

    def test_to_dict(self):
        value_dict = {'v': 234, 'ts': datetime(2022, 3, 15, 12, 40, 53).timestamp(), 'type': None}
        v = Value(**value_dict)
        self.assertIsInstance(v.ts, datetime)
        dic = v.to_dict()
        self.assertEqual(value_dict, dic)
        self.assertNotIsInstance(dic['ts'], datetime)


if __name__ == '__main__':
    unittest.main()
