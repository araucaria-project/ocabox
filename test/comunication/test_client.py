import asyncio
import datetime
import logging
import time
import unittest
from typing import List
from ob.comunication.client import Client
from ob.comunication.comunication_error import CommunicationRuntimeError, CommunicationTimeoutError
from ob.comunication.message_serializer import MessageSerializer
from ob.comunication.multipart_structure import MultipartStructure
from ob.data_colection.address import AddressError
from ob.comunication.router import Router
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse
from test.comunication.sample_test_resolver import SampleTestResolver

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class ClientTest(unittest.TestCase):

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
        # TODO MIKOŁAJ dlaczeg omuszę jawnie niszczyć obiekt bo sam robi to za późno i nie zdąży przed kolejnym testem?
        super().tearDown()

    @staticmethod
    def multipart_to_V_response(resp):
        try:
            vr = ValueResponse.from_byte(resp)
        except TypeError:
            vr = ValueResponse('', None, False, None)
        except AddressError:
            vr = ValueResponse('', None, False, None)
        except ValueError:
            vr = ValueResponse('', None, False, None)
        return vr

    def test_has_cfg(self):
        """
        This checks for critical configuration in default file. Always should return something.

        :return:
        """
        client = Client(name='SampleTestClient')
        self.assertIsNone(client._get_cfg('this_is_not_in_config_file'))
        self.assertIsNotNone(client._get_cfg('port'))
        self.assertIsNotNone(client._get_cfg('url'))
        self.assertIsNotNone(client._get_cfg('protocol'))
        self.assertIsNotNone(client._get_cfg('timeout'))

    def test__check_message_comes(self):
        """
        Test method _check_message_comes()
        """
        client = Client(name='SampleTestClient')
        msg_time = client._get_msg_create_time()
        msg_id = b'0'
        msg_wrong_id = b'1'
        msg_timeout = MessageSerializer.pack_b(time.time() + 100)
        sample_message = [b'', msg_time, msg_id, msg_timeout, b'', b'sample_data']
        ms = MultipartStructure(sample_message)
        client._new_msgs.append(ms)

        self.assertIsNone(client._check_message_comes(msg_time, msg_wrong_id))
        self.assertIsNotNone(client._check_message_comes(msg_time, msg_id))
        self.assertTrue(isinstance(client._check_message_comes(msg_time, msg_id), MultipartStructure))

    def test_get_async_ordered_response(self):
        """
        Test getting many requests by one client and retry ordered responses
        """
        class SampleTestResolverMix(SampleTestResolver):

            async def get_answer(self, request: List[bytes]) -> List[bytes]:
                v_request = ValueRequest.from_byte(request[0])
                nr = v_request.address[v_request.address.get_last_index()]
                nr = int(nr)
                await asyncio.sleep(5 / 10 - nr / 10)
                response = ValueResponse(v_request.address, Value(nr, datetime.datetime.now()))
                return [response.to_byte()]

        self.vr.request_solver = SampleTestResolverMix(None)
        client = Client(name='SampleTestClient')
        client2 = Client(name='SampleTestClient')

        async def coro():
            task1 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.1',
                                                                            datetime.datetime.now(), 20).to_byte()))
            task2 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.2',
                                                                            datetime.datetime.now(), 20).to_byte()))
            task3 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                            datetime.datetime.now(), 20).to_byte()))
            task4 = asyncio.create_task(client2.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.4',
                                                                             datetime.datetime.now(), 20).to_byte()))
            task5 = asyncio.create_task(client2.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                             datetime.datetime.now(), 20).to_byte()))

            result = self.multipart_to_V_response(await task1)
            self.assertEqual(result.value.v, 1)
            logger.info(f"OK: {result.value.v}={1}")
            result = self.multipart_to_V_response(await task2)
            self.assertEqual(result.value.v, 2)
            logger.info(f"OK: {result.value.v}={2}")
            result = self.multipart_to_V_response(await task3)
            self.assertEqual(result.value.v, 3)
            logger.info(f"OK: {result.value.v}={3}")
            result = self.multipart_to_V_response(await task4)
            self.assertEqual(result.value.v, 4)
            logger.info(f"OK: {result.value.v}={4}")
            result = self.multipart_to_V_response(await task5)
            self.assertEqual(result.value.v, 3)
            logger.info(f"OK: {result.value.v}={3}")

            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())

    def test_crash_waiting_task(self):
        """
        This is testing of situation when task witch waiting for response was canceled before retrieve all messages.
        """
        self.vr.request_solver.response_delay = 1  # give a time
        client = Client(name='SampleTestClient')

        async def coro():
            task1 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.1',
                                                                            datetime.datetime.now(), 20).to_byte()))
            task2 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.2',
                                                                            datetime.datetime.now(), 20).to_byte()))
            task3 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                            datetime.datetime.now(), 20).to_byte()))
            await asyncio.sleep(0)
            self.assertEqual(client._waiting_amount, 3)
            self.assertIsNotNone(client._receive_task)
            self.assertIsNotNone(client._loop)

            client._receive_task.cancel()
            await asyncio.sleep(0)
            self.assertIsNotNone(client._receive_task)
            self.assertIsNotNone(client._loop)

            with self.assertRaises(CommunicationRuntimeError):
                result = self.multipart_to_V_response(await task1)
            with self.assertRaises(CommunicationRuntimeError):
                result = self.multipart_to_V_response(await task2)
            with self.assertRaises(CommunicationRuntimeError):
                result = self.multipart_to_V_response(await task3)
            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())

    def test_timeout(self):
        """
        Test when router not responding before timeout
        """
        self.vr.request_solver.response_delay = 10  # give a time
        client = Client(name='SampleTestClient')
        client.default_timeout = 0.2

        async def coro():
            task1 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.1',
                                                                            datetime.datetime.now(), 20).to_byte()))
            task2 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.2',
                                                                            datetime.datetime.now(), 20).to_byte()))
            task3 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                            datetime.datetime.now(), 20).to_byte()))

            await asyncio.sleep(0)

            with self.assertRaises(CommunicationTimeoutError):
                result = self.multipart_to_V_response(await asyncio.wait_for(task1, timeout=client.default_timeout * 2))
            with self.assertRaises(CommunicationTimeoutError):
                result = self.multipart_to_V_response(await asyncio.wait_for(task2, timeout=client.default_timeout * 2))
            with self.assertRaises(CommunicationTimeoutError):
                result = self.multipart_to_V_response(await asyncio.wait_for(task3, timeout=client.default_timeout * 2))
            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()
