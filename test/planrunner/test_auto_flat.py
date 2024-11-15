import unittest
import logging
from ob.planrunner.subcommands.auto_flat import AutoFlatNoTest


logger = logging.getLogger(__name__.rsplit('.')[-1])


class TestAutoFlatNoTest(unittest.IsolatedAsyncioTestCase):

    async def test_auto_flat_no_t_single(self):
        _min_result = 1
        _max_result = 1.25
        single_exposure = AutoFlatNoTest()
        single_exposure.ts_start = [5]
        single_exposure.exposure = [1]
        single_exposure.saturation = [20000]
        single_exposure.evening = True
        _min, _max = await single_exposure._calculate_exposure_time(test_time=200)
        # print(_min, _max)
        self.assertAlmostEqual(first=_min_result, second=_min, places=2)
        self.assertAlmostEqual(first=_max_result, second=_max, places=2)

    async def test_auto_flat_no_t_double(self):
        _min_result = 1
        _max_result = 1.25
        double_exposure = AutoFlatNoTest()
        double_exposure.ts_start = [48, 99]
        double_exposure.exposure = [4, 2]
        double_exposure.zero_level = 0
        double_exposure.saturation = [20000, 20000]
        double_exposure.evening = True
        _min, _max = await double_exposure._calculate_exposure_time(test_time=200)
        self.assertEqual(first=_min_result, second=_min)
        self.assertEqual(first=_max_result, second=_max)

    async def test_auto_flat_no_t_triple(self):
        """
        sat 	dt_start 	exp 	sat_sec 	dt_start_t 	ts_start 	ts_mid 	ts_mid_shift
        0 	20000 	... 	4.38 	4566.210046 	... 	1.731490e+09 	1.731490e+09 	0.000000
        1 	20000 	... 	3.80 	5263.157895 	... 	1.731490e+09 	1.731490e+09 	28.779058
        2 	20000 	... 	3.35 	5970.149254 	... 	1.731490e+09 	1.731490e+09 	56.916811
        3 	20000 	... 	2.94 	6802.721088 	... 	1.731490e+09 	1.731490e+09 	85.610859
        4 	20000 	... 	2.60 	7692.307692 	... 	1.731490e+09 	1.731490e+09 	113.091822
        5 	20000 	... 	2.29 	8733.624454 	... 	1.731490e+09 	1.731490e+09 	140.547465
        6 	20000 	... 	2.04 	9803.921569 	... 	1.731490e+09 	1.731490e+09 	166.911597

        """

        _min_result = 2.04
        triple_exposure = AutoFlatNoTest()
        triple_exposure.ts_start = [
            0,
            28.779058,
            56.916811,
            85.610859,
            113.091822
        ]
        triple_exposure.exposure = [4.38, 3.80 , 3.35, 2.94, 2.60]
        triple_exposure.zero_level = 290
        triple_exposure.saturation = [
            20000,
            20000,
            20000,
            20000,
            20000
        ]
        triple_exposure.evening = True
        _min, _max = await triple_exposure._calculate_exposure_time(test_time=166.911597)
        self.assertAlmostEqual(first=_min_result, second=_min, places=1)

    async def test_auto_flat_real_dat_1(self):

        _min_result = 2.04
        triple_exposure = AutoFlatNoTest()
        triple_exposure.ts_start = [
            0.0,
            22.233521699905396,
            51.232887744903564,
            79.2319598197937,
            # 107.23099780082703
        ]
        triple_exposure.exposure = [
            1.0,
            3.467043486188349,
            3.4657752780152546,
            3.463919431276164,
            # 3.4619957539940116
        ]
        triple_exposure.zero_level = 290
        triple_exposure.saturation = [
            6469.5, 21534.0, 24284.0, 27345.0,
            # 30686.0
        ]
        triple_exposure.evening = True
        _min, _max = await triple_exposure._calculate_exposure_time(test_time=107.23099780082703)
        # print(_min, _max)
        self.assertAlmostEqual(first=_min_result, second=_min, places=1)

    async def test_auto_flat_evaluate_exposure_time(self):
        # Case 1 evening exposure min is ok
        afnt = AutoFlatNoTest()
        afnt.range_min_max_time_exp = [2, 30]
        test_1 = 2.5
        test_2 = 0
        afnt.evening = True
        ret1, ret2 = await afnt._evaluate_exposure_time(
            exposure_min=2.5,
            exposure_max=3,
            test=True
        )
        # print(ret1, ret2)
        self.assertEqual(first=ret1, second=test_1)
        self.assertEqual(first=ret2, second=test_2)

        # Case 2 evening exposure range_min exposure is ok
        afnt = AutoFlatNoTest()
        afnt.range_min_max_time_exp = [2, 30]
        test_1 = 2
        test_2 = 0
        afnt.evening = True
        ret1, ret2 = await afnt._evaluate_exposure_time(
            exposure_min=1,
            exposure_max=3,
            test=True
        )
        # print(ret1, ret2)
        self.assertEqual(first=ret1, second=test_1)
        self.assertEqual(first=ret2, second=test_2)

        # Case 3 evening skip filter
        afnt = AutoFlatNoTest()
        afnt.range_min_max_time_exp = [2, 30]
        test_1 = 0
        test_2 = 1
        afnt.evening = True
        ret1, ret2 = await afnt._evaluate_exposure_time(
            exposure_min=40,
            exposure_max=60,
            test=True
        )
        # print(ret1, ret2)
        self.assertEqual(first=ret1, second=test_1)
        self.assertEqual(first=ret2, second=test_2)

        # Case 4 evening do test exposure
        afnt = AutoFlatNoTest()
        afnt.range_min_max_time_exp = [2, 30]
        test_1 = None
        test_2 = None
        afnt.evening = True
        ret1, ret2 = await afnt._evaluate_exposure_time(
            exposure_min=0.5,
            exposure_max=1,
            test=True
        )
        # print(ret1, ret2)
        self.assertEqual(first=ret1, second=test_1)
        self.assertEqual(first=ret2, second=test_2)

        # Case 5 morning skip filter
        afnt = AutoFlatNoTest()
        afnt.range_min_max_time_exp = [2, 30]
        test_1 = 0
        test_2 = 1
        afnt.evening = False
        ret1, ret2 = await afnt._evaluate_exposure_time(
            exposure_min=0.5,
            exposure_max=1,
            test=True
        )
        # print(ret1, ret2)
        self.assertEqual(first=ret1, second=test_1)
        self.assertEqual(first=ret2, second=test_2)

        # Case 6 morning do test exposure
        afnt = AutoFlatNoTest()
        afnt.range_min_max_time_exp = [2, 30]
        test_1 = None
        test_2 = None
        afnt.evening = False
        ret1, ret2 = await afnt._evaluate_exposure_time(
            exposure_min=40,
            exposure_max=50,
            test=True
        )
        # print(ret1, ret2)
        self.assertEqual(first=ret1, second=test_1)
        self.assertEqual(first=ret2, second=test_2)

if __name__ == '__main__':
    unittest.main()
