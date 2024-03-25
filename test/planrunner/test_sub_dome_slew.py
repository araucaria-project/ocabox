
import unittest
from ocaboxapi.telescope import Telescope
from ocaboxapi.observatory import Observatory
import logging
import math
from pyaraucaria.coordinates import site_sidereal_time, ra_dec_2_az_alt, ra_to_decimal


logger = logging.getLogger(__name__.rsplit('.')[-1])


class EqDomeSlewTest(unittest.TestCase):

    # def test_eq_dome_slew(self):
    #     # obs = Observatory()
    #     # t = Telescope(id='dev', observatory=obs)
    #     # ds = DomeSlew(id='', telescope=t, info_callback={}, uobi=22)
    #     OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
    #     r_dome = 3500.0
    #     spx = -250.0
    #     spy = 200.0
    #     gem = 680.0
    #     ra = ra_to_decimal('17:31:30')
    #     az, alt = ra_dec_2_az_alt(ra=ra,
    #                             dec=-20.83,
    #                             latitude=OCA['latitude'],
    #                             longitude=OCA['longitude'],
    #                             elevation=OCA['elevation'],
    #                             epoch='2000')
    #     print(ra)
    #     print(alt, ' ', az)
    #     eq_dome_slew = dome_eq_azimuth(ra=ra, dec=-20.3, r_dome=r_dome, spx=spx, spy=spy,
    #                                       gem=gem, side_of_pier=1, latitude=OCA['latitude'],
    #                                       longitude=OCA['longitude'], elevation=OCA['elevation'])
    pass

if __name__ == '__main__':
    unittest.main()
