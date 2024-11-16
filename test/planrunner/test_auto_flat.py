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

        _min_result = 28.39
        triple_exposure = AutoFlatNoTest()
        triple_exposure.zero_level = 985
        ts = [1731747996.3501148, 1731748015.2929509, 1731748034.1337261, 1731748053.092465,
                              1731748071.6134248, 1731748090.8051546, 1731748110.106679, 1731748129.6404352,
                              1731748149.0351684, 1731748168.9507198, 1731748188.9193718, 1731748208.6133432,
                              1731748228.07451, 1731748247.0922816, 1731748266.6200738, 1731748286.2208922,
                              1731748305.7002723, 1731748325.0519543, 1731748345.2274277, 1731748364.8947246,
                              1731748384.123295, 1731748403.958688, 1731748423.4948268, 1731748443.385234,
                              1731748463.3134286,
                                    # 1731759283.288294,
                                    # 1731748534.7738519
                                    ]


        triple_exposure.ts_start = (np.array(ts) + 10800).tolist()
        triple_exposure.saturation = [1120.59, 1128.45,
            1136.33, 1146.11,
            1151.64, 1164.42,
            1175.09, 1186.0,
            1196.82, 1215.04,
            1224.27, 1242.16,
            1261.55, 1276.7,
            1299.37, 1318.31,
            1339.72, 1369.14,
            1392.61, 1423.51,
            1451.16, 1484.27,
            1525.65, 1566.8,
            1610.08,
                                      # 20398,
            # 1810.17
                                      ]
        triple_exposure.exposure = [
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            # 28.398909393878885,
            # 1.0
        ]

        triple_exposure.evening = True
        _min, _max = await triple_exposure._calculate_exposure_time(test_time=1731759283.288294)
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
