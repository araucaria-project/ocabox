import asyncio
import unittest

import requests

from ob.data_colection.alpaca_api.observatory import Observatory
import logging
logger = logging.getLogger(__name__)


class ObservatoryTest(unittest.TestCase):

    def _setUpLoop(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def setUp(self):
        super().setUp()
        self._setUpLoop()

    def _tearDownLoop(self) -> None:
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

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_something(self):

        observatory = Observatory()

        observatory.connect('dibi-camk')

        tel = observatory.dibi  # sys_id "my_telescope" is a key in config file

        async def coro():
            a = await tel.targetdeclination(1.0)
            print(a)

        self.loop.run_until_complete(coro())
        self.assertEqual(True, True)  # add assertion here


if __name__ == '__main__':
    unittest.main()
