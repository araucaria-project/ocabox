from ob.planrunner.cycle_time_calc.abstract_cycle_time import AbstractCycleTime
import unittest
import numpy as np

class TestCycleTime(unittest.TestCase):

    def test_alt_az_distance(self):

        az_start = 0
        az_end = 90
        alt_start = 0
        alt_end = 0
        res = 90
        c = AbstractCycleTime.alt_az_distance(start_az=az_start, end_az=az_end, start_alt=alt_start, end_alt=alt_end)
        self.assertEqual(res, c)

    def test_vector(self):

        az_end = 90
        alt_end = 0
        c2r = np.array([1.0, 0.0, 0.0])
        c2 = AbstractCycleTime.vector(alt=alt_end, az=az_end)
        if c2.all() == c2r.all():
            r=1
        else:
            r=0
        self.assertEqual(first=1, second=r)


if __name__ == '__main__':
    unittest.main()