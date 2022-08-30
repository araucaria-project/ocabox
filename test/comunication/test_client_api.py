import asyncio
import logging
import time
import unittest
from ob.comunication.client_api import ClientAPI
from ob.comunication.router import Router
from ob.data_colection.value_call import ValueResponse, ValueRequest
from test.comunication.sample_test_resolver import SampleTestResolver

logger = logging.getLogger(__name__)


class ClientAPITest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        name = 'SampleTestRouter'
        self.vr = Router(SampleTestResolver(None), name=name)
        self.vr.start(self.loop)

    def tearDown(self) -> None:
        self.vr.stop()
        vr_stop = asyncio.gather(self.vr.get_stop_task(), return_exceptions=True)
        self.loop.run_until_complete(vr_stop)

        try:
            all_tasks = asyncio.all_tasks(self.loop)
            for t in all_tasks:
                t.cancel()
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            all_tasks = asyncio.all_tasks(self.loop)
            if not all_tasks:
                logger.info('All task in loop is finished')
            else:
                logger.error('Some of the tasks in current loop is still running')
                raise RuntimeError
        finally:
            asyncio.set_event_loop(None)
            self.loop.close()
        self.vr.__del__()
        super().tearDown()

    def test_initial_client_api(self):
        c_api = ClientAPI()
        self.assertIsNotNone(c_api.client)

    def test_get_multi(self):
        """
        Test method get_multi()
        """
        c_api = ClientAPI(name='SampleTestClient')

        async def coro():
            request = [ValueRequest('sample_telescope.dibi.azimuth.1', time.time(), 20),
                       ValueRequest('sample_telescope.dibi.azimuth.2', time.time(), 20)]
            task1 = asyncio.create_task(c_api.send_multi(request))
            result = await task1
            # self.assertEqual(len(result), len(request))
            self.assertTrue(isinstance(result[0], ValueResponse))
            self.assertIsNotNone(result[0].value.v)
            self.assertIsNotNone(result[1].value.v)

        self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()
