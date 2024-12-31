
import unittest

from ob.planrunner.subcommands.sub_mount_slew import MountSlew
from ocaboxapi.telescope import Telescope
from ocaboxapi.observatory import Observatory
import logging
import math
from pyaraucaria.coordinates import site_sidereal_time, ra_dec_2_az_alt, ra_to_decimal


logger = logging.getLogger(__name__.rsplit('.')[-1])


class MountDitherRaSlewTest(unittest.TestCase):

    def test_mount_dither_ra_slew(self):
        ra_dit_max = 1.53
        dec = -90
        # print(math.cos(math.radians(85)))
        # print(math.cos(math.radians(60)))
        # print(math.cos(math.radians(40)))
        # print(math.cos(math.radians(20)))
        # print(math.cos(math.radians(0)))
        # print(math.cos(math.radians(-20)))
        # print(math.cos(math.radians(-40)))
        # print(math.cos(math.radians(-60)))
        # print(math.cos(math.radians(-85)))
        ra_dit = MountSlew.ra_random_dither(0, dec, 8)
        print(ra_dit)
        self.assertLess(abs(ra_dit), ra_dit_max)

        ra_dit_max = 0.14
        dec = 0
        ra_dit = MountSlew.ra_random_dither(0, dec, 8)
        print(ra_dit)
        self.assertLess(abs(ra_dit), ra_dit_max)

if __name__ == '__main__':
    unittest.main()
