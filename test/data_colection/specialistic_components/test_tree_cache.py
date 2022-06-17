import datetime
import unittest

from ob.data_colection.address import Address
from ob.data_colection.specialistic_components.tree_cache import TreeCache
from ob.data_colection.value import Value


class TreeCacheTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.v1 = ('val1', Value(1, datetime.datetime(2022, 5, 20, 1, 1, 1)))
        self.v2 = ('val2', Value(2, datetime.datetime(2022, 5, 20, 2, 2, 2)))
        self.v3 = ('val3', Value(3, datetime.datetime(2022, 5, 20, 3, 3, 3)))
        self.v4 = ('val4', Value(4, datetime.datetime(2022, 5, 20, 4, 4, 4)))

    def tearDown(self) -> None:
        super().tearDown()

    def test__value_meets_requirements(self):
        """
        test method _value_meets_requirements()
        :return:
        """
        address = Address('.'.join(['sample_address', self.v1[0]]))
        kv = TreeCache._KnownValue(address, self.v1[1], None)

        expected_date = self.v1[1].ts + datetime.timedelta(seconds=10)
        result = TreeCache._value_meets_requirements(kv, expected_date, 20)
        self.assertTrue(result)
        result = TreeCache._value_meets_requirements(kv, expected_date, 10)
        self.assertTrue(result)
        result = TreeCache._value_meets_requirements(kv, expected_date, 5)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
