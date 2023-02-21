import asyncio
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
from ob.util_functions.asyncio_util_functions import wait_for_psce
from test.comunication.sample_test_resolver import SampleTestResolver

logger = logging.getLogger(__name__.rsplit('.')[-1])
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

            async def get_answer(self, request: List[bytes], user_id: bytes, timeout=None) -> List[bytes]:
                v_request = ValueRequest.from_byte(request[0])
                nr = v_request.address[v_request.address.get_last_index()]
                nr = int(nr)
                await asyncio.sleep(5 / 10 - nr / 10)
                response = ValueResponse(v_request.address, Value(nr, time.time()))
                return [response.to_byte()]

        self.vr.request_solver = SampleTestResolverMix(None)
        client = Client(name='SampleTestClient')
        client2 = Client(name='SampleTestClient')

        async def coro():
            task1 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.1',
                                                                            time.time(), 20).to_byte()))
            task2 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.2',
                                                                            time.time(), 20).to_byte()))
            task3 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                            time.time(), 20).to_byte()))
            task4 = asyncio.create_task(client2.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.4',
                                                                             time.time(), 20).to_byte()))
            task5 = asyncio.create_task(client2.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                             time.time(), 20).to_byte()))

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
                                                                            time.time(), 20).to_byte()))
            task2 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.2',
                                                                            time.time(), 20).to_byte()))
            task3 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                            time.time(), 20).to_byte()))
            await asyncio.sleep(0.1)  # have to be more than 0 !
            self.assertEqual(client._waiting_amount, 3)
            self.assertIsNotNone(client._receive_task)
            self.assertIsNotNone(client._loop)

            client._receive_task.cancel()
            await asyncio.sleep(0.1)  # have to be more than 0 !
            # none because before ending all waiting task was stop and last one remove _loop and _receive_task
            self.assertIsNone(client._receive_task)

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
                                                                            time.time(), 20).to_byte()))
            task2 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.2',
                                                                            time.time(), 20).to_byte()))
            task3 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.3',
                                                                            time.time(), 20).to_byte()))

            await asyncio.sleep(0)

            with self.assertRaises(CommunicationTimeoutError):
                result = self.multipart_to_V_response(await wait_for_psce(task1, timeout=client.default_timeout * 2))
            with self.assertRaises(CommunicationTimeoutError):
                result = self.multipart_to_V_response(await wait_for_psce(task2, timeout=client.default_timeout * 2))
            with self.assertRaises(CommunicationTimeoutError):
                result = self.multipart_to_V_response(await wait_for_psce(task3, timeout=client.default_timeout * 2))
            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())

    def test_clearing_list_new_msgs(self):
        """Test when client retrieve message and no one read it before timeout."""
        client = Client(name='SampleTestClient')
        client.default_timeout = 0.2
        client._cleaning_length = 5

        async def coro():
            old_ms = MultipartStructure([b'',
                                         b'2222222',
                                         b'0',
                                         MessageSerializer.pack_b(time.time() - 1),
                                         b'', ValueResponse('some.some').to_byte()])
            client._new_msgs.append(old_ms)
            self.assertTrue(len(client._new_msgs) == 1)
            task1 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.1',
                                                                            time.time(), 20).to_byte()))
            await asyncio.sleep(0)
            self.assertTrue(len(client._new_msgs) > 0)  # old message is on the list
            result = self.multipart_to_V_response(await wait_for_psce(task1, timeout=client.default_timeout * 2))
            self.assertTrue(len(client._new_msgs) > 0)  # old message steal is on the list because _cleaning_length
            # param is higher than 0

            # now set the _cleaning_length to 0 and send request again
            client._cleaning_length = 0
            task2 = asyncio.create_task(client.send_singlepart(ValueRequest('sample_telescope.dibi.azimuth.2',
                                                                            time.time(), 20).to_byte()))
            await asyncio.sleep(0)
            result = self.multipart_to_V_response(await wait_for_psce(task2, timeout=client.default_timeout * 2))
            self.assertTrue(len(client._new_msgs) == 0)  # list is empty because task get his message and clear list
            # from old messages
            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())

    def test_fast_rebooting_receive_task(self):
        """This test is enough that it does not throw any errors.
        This test checks if there is a problem with the timing of closing and opening the task when sending quick
        queries when the receive task is exiting and reopening. Before the old task closed and the event was set
        to None, the new one started and set the correct new Event, and then the old task deleted the Event, and then
        it was attempted to refer to the None methods, and it caused a crash."""
        client = Client(name='SampleTestClient')
        client.default_timeout = 0.2
        client._cleaning_length = 5

        async def task_coro():
            await client.send_multipart([ValueRequest('sample_telescope.dibi.azimuth.1',
                                                      time.time(), 20).to_byte()])
            # allow the client to start shutting down the task to receive a reply from the server
            await asyncio.sleep(0)
            # only check for the last task
            if client._waiting_amount == 0:
                self.assertTrue(client._msg_event is not None)
            # make fast response again
            await client.send_multipart([ValueRequest('sample_telescope.dibi.azimuth.1',
                                                      time.time(), 20).to_byte()])

        async def coro():
            task1 = asyncio.create_task(task_coro())
            task2 = asyncio.create_task(task_coro())
            await task1
            await task2

        self.loop.run_until_complete(coro())

    def test_cancel_receive_message(self):
        """
        Test a situation where a sub-task created by asyncio.wait_for() is in the done state but the wait_for()
        method has not read its status yet and at this moment there is a canceled task with the wait_for() method.
        In such a situation, the wait_for() method will suppress the asyncio.CanceledError error, which is
        unacceptable. The problem is difficult to reproduce in a full environment and occurs intermittently.
        Occurred while testing cycle_query and was tested there. The solution is to use the wait_for_psce() method
        instead of the original asyncio._wait_for() method.
        """

        async def waiting_coro():
            # this method quickly completes and returns some value
            await asyncio.sleep(0)
            return 4

        async def task_coro():
            # this is a main task body
            return await wait_for_psce(waiting_coro(), 10)

        async def coro():
            # this is the service method to trigger the event
            task1 = asyncio.create_task(task_coro())

            # wait two times
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            task1.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task1

        self.loop.run_until_complete(coro())

    def test_synchronization_receiver_task(self):
        """
        Test the situation when the retrieve task starts and receive a message faster than the main task will start
        waiting for condition. In this situation, condition should be blocked until the main task starts waiting for it.
        """

        class ClientFastRetriever(Client):
            """
            This client is supposed to trigger a situation where the retrieve task will receive the message before
            the main task waits for condition
            """

            async def _stand_in_line(self):
                await super()._stand_in_line()
                await asyncio.sleep(0.2)  # let the retrieve task start and retrieve first message

        client = ClientFastRetriever(name='SampleTestClient')
        client.default_timeout = 0.5

        async def coro():

            result = await client.send_singlepart(
                    ValueRequest('sample_telescope.dibi.azimuth.1', time.time(), 20).to_byte())
            # can not raisa a CommunicationTimeoutError

        self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()
