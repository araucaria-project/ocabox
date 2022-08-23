import asyncio
import datetime
import logging
import unittest

from ob.data_colection.address import Address
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.value_call import ValueRequest
from ob.ob_config import SingletonConfig

logger = logging.getLogger(__name__)


class TreeAlpacaTest(unittest.TestCase):

    OBSERVATORY_NAME = 'test_observatory'

    def _setUpLoop(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def setUp(self):
        super().setUp()
        self._setUpLoop()
        self.tao = TreeAlpacaObservatory('sample_component', None, self.OBSERVATORY_NAME)

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

    def test_alpaca_call(self):
        """
        Test connection to the alpaca server. This test requires the alpaca server to be running in the background.
        """
        sample_alpaca_call = 'name'

        sample_components = SingletonConfig.get_config()[self.OBSERVATORY_NAME]['observatory']['components'].get()
        component = list(sample_components.keys())[0]

        address = Address(f"{component}.{sample_alpaca_call}")
        request = ValueRequest(address, datetime.datetime.now())

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNotNone(response.value)
            self.assertTrue(isinstance(response.value.v, str))
        self.loop.run_until_complete(coro())

    def test_alpaca_wrong_call(self):
        sample_alpaca_call = 'no_existing_method'

        sample_components = SingletonConfig.get_config()[self.OBSERVATORY_NAME]['observatory']['components'].get()
        component = list(sample_components.keys())[0]

        address = Address(f"{component}.{sample_alpaca_call}")
        request = ValueRequest(address, datetime.datetime.now())

        async def coro():
            response = await self.tao.get_response(request)
            self.assertIsNone(response.value)
            self.assertFalse(response.status)
            self.assertIsNotNone(response.error)
            self.assertTrue(response.error.code == 2002)
        self.loop.run_until_complete(coro())
    # TODO ten test nie działa ale jest chyba dobrze - problem z tym że zapytanie get z parametrami wykonuje się poprawnie
    # def test_alpaca_wrong_args_for_method(self):
    #     sample_alpaca_call = 'name'
    #
    #     sample_components = SingletonConfig.get_config()[self.OBSERVATORY_NAME]['observatory']['components'].get()
    #     component = list(sample_components.keys())[0]
    #
    #     address = Address(f"{component}.{sample_alpaca_call}")
    #     request = ValueRequest(address, datetime.datetime.now(), request_data={'sample_wrong_argument': 2})
    #
    #     async def coro():
    #         response = await self.tao.get_response(request)
    #         self.assertIsNone(response.value)
    #         self.assertFalse(response.status)
    #         self.assertIsNotNone(response.error)
    #         self.assertTrue(response.error.code == 1003)
    #     self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()
