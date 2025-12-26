import unittest
import logging

import numpy as np

from ob.planrunner.subcommands.auto_flat import AutoFlatNoTest


logger = logging.getLogger(__name__.rsplit('.')[-1])


class TestAutoFlatNoTest(unittest.IsolatedAsyncioTestCase):

    async def test_auto_flat_no_t_single(self):
        _min_result = 1
        _max_result = 1.25
        single_exposure = AutoFlatNoTest()
        single_exposure.ts_start = [5]
        single_exposure.exposure = [1]
        single_exposure.adu = [20000]
        single_exposure.evening = True
        _min, _max = await single_exposure._calculate_exposure_time(test_time=10)
        # print(_min, _max)
        self.assertAlmostEqual(first=_min_result, second=_min, places=2)
        self.assertAlmostEqual(first=_max_result, second=_max, places=2)

    async def test_auto_flat_no_t_single_too_old(self):
        _min_result = None
        _max_result = None
        single_exposure = AutoFlatNoTest()
        single_exposure.ts_start = [5]
        single_exposure.exp_type = ['f', 't']
        single_exposure.exposure = [1]
        single_exposure.adu = [20000]
        single_exposure.evening = True
        _min, _max = await single_exposure._calculate_exposure_time(test_time=300)
        print(_min, _max)
        self.assertAlmostEqual(first=_min_result, second=_min, places=2)
        self.assertAlmostEqual(first=_max_result, second=_max, places=2)

    async def test_auto_flat_no_t_double(self):
        _min_result = 1
        _max_result = 1.25
        double_exposure = AutoFlatNoTest()
        double_exposure.ts_start = [48, 99]
        double_exposure.exposure = [4, 2]
        double_exposure.exp_type = ['f', 't']
        double_exposure.zero_level = 0
        double_exposure.adu = [20000, 20000]
        double_exposure.evening = True
        _min, _max = await double_exposure._calculate_exposure_time(test_time=200)
        self.assertEqual(first=_min_result, second=_min)
        self.assertEqual(first=_max_result, second=_max)

    async def test_auto_flat_no_t_double_too_old(self):
        _min_result = None
        _max_result = None
        double_exposure = AutoFlatNoTest()
        double_exposure.ts_start = [48, 99]
        double_exposure.exposure = [4, 2]
        double_exposure.exp_type = ['f', 't']
        double_exposure.zero_level = 0
        double_exposure.adu = [20000, 20000]
        double_exposure.evening = True
        _min, _max = await double_exposure._calculate_exposure_time(test_time=400)
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
        triple_exposure.exp_type = ['f', 't']
        triple_exposure.adu = [
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

        _min_result = 10.16610803879626
        triple_exposure = AutoFlatNoTest()
        triple_exposure.range_min_max_adu = [40000, 60000]
        triple_exposure.range_min_max_time_exp = [10, 120]
        triple_exposure.zero_level = 3817
        triple_exposure.exp_type = [
            't', 't', 't', 't', 't', 't',

            't', 't', 't', 't', 't', 't',

            't', 't', 't', 't', 't', 't',

            't', 't', 't' ,'t', 'f' ,'f',

            'f'
        ]

        ts = [
            0., 38.86849999, 75.31322718, 114.67441201, 153.80733109,
            192.38675308, 230.33049703, 266.73679304, 304.79577208, 343.8199842,
            384.47323418, 422.83736014, 461.75713706, 499.92938304, 538.84837699,
            579.50246906, 617.97130799, 657.3219862, 695.84400821, 734.78558207,
            775.39432216, 814.85847616, 852.51737499, 906.4082582,
            # 957.53602815
        ]


        triple_exposure.ts_start = ts #(np.array(ts) + 10800).tolist()
        triple_exposure.adu = [
            170399.3425, 158904.675, 140978.36, 122679.47, 106211.4625, 92026.645,
            79967.5225, 69173.7625, 59877.115, 51212.51, 43655.79, 37555.4125,
            32259.7925, 27871.3725, 24124.5825, 20836.695, 18231.3225, 16012.0375,
            14180.805, 12639.6675, 11300.8375, 10222.12, 56387., 47239.,
            # 40204.
        ]
        triple_exposure.exposure = [
            1., 1., 1., 1., 1., 1.,
            1., 1., 1., 1., 1., 1.,
            1., 1., 1., 1., 1., 1.,
            1., 1., 1. ,1., 10. ,10.,
            # 10.1608111
        ]

        triple_exposure.evening = True
        _min, _max = await triple_exposure._calculate_exposure_time(
            test_time=957.53602815
            # test_time = 1010
        )
        # print(_min, _max)
        self.assertAlmostEqual(first=_min_result, second=_min, places=1)

    async def test_auto_flat_evaluate_exposure_time(self):
        # Case 1 evening exposure min is ok
        afnt = AutoFlatNoTest()
        afnt.range_min_max_time_exp = [2, 30]
        afnt.exp_type = ['f', 't']
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

    async def test_auto_flat_minus_value_calc(self):
        _min_result = None
        _max_result = None
        double_exposure = AutoFlatNoTest()
        double_exposure.ts_start = [1, 10]
        double_exposure.exposure = [1, 1]
        double_exposure.exp_type = ['f', 't']
        double_exposure.zero_level = 0
        double_exposure.adu = [3500, 500]
        double_exposure.evening = True
        _min, _max = await double_exposure._calculate_exposure_time(test_time=30)
        self.assertEqual(first=_min_result, second=_min)
        self.assertEqual(first=_max_result, second=_max)

if __name__ == '__main__':
    unittest.main()
