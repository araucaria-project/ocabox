import logging
import unittest

from ocaboxapi import Observatory

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ClientAPITest(unittest.TestCase):

    pass
    # def test_get_app_cfg(self):
    #     """Test method get_app_cfg()"""
    #     o = Observatory(client_name="SampleTestClient")
    #     # test get right value
    #     r = o.get_app_cfg("base_fits_dir_test_default")
    #     self.assertEqual(r, "test_dir22")
    #     # test default value from DefaultClient
    #     r = o.get_app_cfg("base_fits_dir")
    #     self.assertEqual(r, "/data/fits/")
    #     # test no existing value
    #     r = o.get_app_cfg("no_existing_value")
    #     self.assertIsNone(r)


if __name__ == '__main__':
    unittest.main()
