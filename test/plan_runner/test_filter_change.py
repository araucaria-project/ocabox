from serverish.messenger import Messenger
from ob.planrunner.config_general import ConfigGeneral
import unittest
import numpy as np


from ocaboxapi import Observatory


class TestFiltersFromGeneralConf(unittest.IsolatedAsyncioTestCase):

    async def test_filters(self):
        nats_messenger = Messenger()
        await nats_messenger.open(host="nats.oca.lan", port=4222, wait=4)

        o = Observatory(client_name="CliClient", config_stream="tic.config.observatory")
        await o.load_client_cfg()
        o.connect()
        cli_conf = o.get_client_configuration()
        for tel in ['zb08', 'wk06', 'jk15']:
            fw = Observatory().get_telescope(telescope_id=tel).get_filterwheel()
            filter_dict = await fw.aget_names()
            print('Dict from a_get  ', filter_dict)
            cg = ConfigGeneral(telescope=Observatory().get_telescope(telescope_id=tel), client_config_dict=cli_conf)
            r = cg.get_value(seq=[
                'telescopes', tel, 'observatory', 'components', 'filterwheel', 'filters'
            ], source='nats')
            rr = {entry['name']: entry['position'] for entry in r}
            # print(r)
            print('Dict from config ', rr)
            self.assertDictEqual(filter_dict, rr)



        # # filter_dict = await self.filterwheel.aget_names()
        #
        # az_start = 0
        # az_end = 90
        # alt_start = 0
        # alt_end = 0
        # res = 90
        # c = AbstractCycleTime.alt_az_distance(start_az=az_start, end_az=az_end, start_alt=alt_start, end_alt=alt_end)
        # self.assertEqual(res, c)




if __name__ == '__main__':
    unittest.main()