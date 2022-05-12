import unittest
from datetime import datetime

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


if __name__ == '__main__':
    unittest.main()
