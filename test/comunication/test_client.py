import asyncio
import datetime
import logging
import unittest
from typing import List

from ob.comunication.client import Client
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.comunication.base_request_solver import BaseRequestSolver
from ob.comunication.router import Router
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class ClientTest(unittest.TestCase):
    class SampleTestResolver(BaseRequestSolver):
        RESPONSE_DELAY = 0

        async def get_answer(self, request: List[dict]) -> List[dict]:
            v_request = ValueRequest.from_dict(request[0])
            await asyncio.sleep(self.response_delay)
            response = ValueResponse(v_request.address, Value('sample_answer', datetime.datetime.now()))
            return [response.to_dict()]

        def __init__(self, data_provider: ProvidesResponseProtocol, **kwargs):
            self.response_delay = self.RESPONSE_DELAY
            super().__init__(data_provider, **kwargs)

    def setUp(self):
        super().setUp()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        name = 'SampleTestRouter'
        self.vr = Router(self.SampleTestResolver(None), name=name)
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
        super().tearDown()

    def test_get_async_ordered_response(self):
        """
        Test getting many requests by one client and retry ordered responses

        :return:
        """

        class SampleTestResolverMix(self.SampleTestResolver):

            async def get_answer(self, request: List[dict]) -> List[dict]:
                v_request = ValueRequest.from_dict(request[0])
                nr = v_request.address[v_request.address.get_last_index()]
                try:
                    nr = int(nr)
                except Exception as e:
                    nr = 0
                await asyncio.sleep(5/10 - nr/10)
                response = ValueResponse(v_request.address, Value(nr, datetime.datetime.now()))
                return [response.to_dict()]

        self.vr.request_solver = SampleTestResolverMix(None)
        client = Client(name='SampleTestClient')
        client2 = Client(name='SampleTestClient')

        async def coro():
            task1 = asyncio.create_task(client.get_async('sample_telescope.dibi.azimuth.1', datetime.datetime.now(), 20))
            task2 = asyncio.create_task(client.get_async('sample_telescope.dibi.azimuth.2', datetime.datetime.now(), 20))
            task3 = asyncio.create_task(client.get_async('sample_telescope.dibi.azimuth.3', datetime.datetime.now(), 20))
            task4 = asyncio.create_task(client2.get_async('sample_telescope.dibi.azimuth.4', datetime.datetime.now(), 20))
            task5 = asyncio.create_task(client2.get_async('sample_telescope.dibi.azimuth.3', datetime.datetime.now(), 20))
            result = await task1
            self.assertEqual(result.value.v, 1)
            logger.info(f"OK: {result.value.v}={1}")
            result = await task2
            self.assertEqual(result.value.v, 2)
            logger.info(f"OK: {result.value.v}={2}")
            result = await task3
            self.assertEqual(result.value.v, 3)
            logger.info(f"OK: {result.value.v}={3}")
            result = await task4
            self.assertEqual(result.value.v, 4)
            logger.info(f"OK: {result.value.v}={4}")
            result = await task5
            self.assertEqual(result.value.v, 3)
            logger.info(f"OK: {result.value.v}={3}")

            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())
