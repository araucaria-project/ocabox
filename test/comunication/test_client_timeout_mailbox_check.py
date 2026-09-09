import asyncio
import time
import types
import unittest

from obcom.comunication.comunication_error import CommunicationTimeoutError
from obcom.comunication.message_serializer import MessageSerializer
from obcom.comunication.multipart_structure import MultipartStructure

from ob.comunication.client import Client


class _FakeFrontSocket:
    LAST_ENDPOINT = "tcp://fake-endpoint:1234"

    async def send_multipart(self, parts):
        return None

    def close(self):
        return None


class _StubClient(Client):
    """
    A Client subclass that bypasses the real receiver task machinery (socket recv loop) while still
    tracking `_waiting_amount`, so tests can focus on the timeout/mailbox-check logic in
    `_send_to_server` without needing a real ZMQ receiver task.
    """

    async def _stand_in_line(self):
        self._waiting_amount += 1

    async def _skip_the_line(self):
        self._waiting_amount -= 1


class TestClientTimeoutMailboxCheck(unittest.IsolatedAsyncioTestCase):

    @staticmethod
    def _make_client():
        client = _StubClient.__new__(_StubClient)
        client._loop = asyncio.get_running_loop()
        client._msg_con = None
        client._recv_lock = None
        client._new_msgs = []
        client._front_socket = _FakeFrontSocket()
        client.context = types.SimpleNamespace(destroy=lambda: None)
        client._name = "test-client"
        client._waiting_amount = 0
        return client

    @staticmethod
    def _make_envelope(create_time: float, msg_id: int):
        create_time_b = MessageSerializer.pack_b(int(create_time))
        id_b = MessageSerializer.pack_b(msg_id)
        timeout_b = MessageSerializer.pack_b(time.time() + 100)
        return MultipartStructure.from_parts(create_time=create_time_b, id_=id_b, data=[b'reply-data'],
                                             request_timeout=timeout_b, prefix_data=[])

    def _patch_wait_for_response(self, schedule_append=None):
        """Patch `Client._wait_for_response` (awaited inside the `async with asyncio.timeout(...)`
        block in `_send_to_server`) so it never completes on its own, optionally scheduling a
        mailbox append via `call_soon` first. The real `asyncio.timeout()` then fires after
        `time_to_expire` seconds, cancelling this coroutine, so the append becomes visible before
        the timeout fires and `_send_to_server` can find it during its post-timeout mailbox check."""

        async def _fake_wait_for_response(self_inner, msg_create_time_b, msg_id_b):
            if schedule_append is not None:
                asyncio.get_running_loop().call_soon(schedule_append)
            await asyncio.Event().wait()  # never completes; cancelled when the timeout fires

        original = _StubClient._wait_for_response
        _StubClient._wait_for_response = _fake_wait_for_response
        self.addCleanup(setattr, _StubClient, "_wait_for_response", original)

    async def test_reply_in_mailbox_at_timeout_is_returned(self):
        """Reply present at timeout -> returned, no exception raised."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=1)
        reply = self._make_envelope(create_time=MessageSerializer.unpack_b(ms.create_time), msg_id=1)

        self._patch_wait_for_response(schedule_append=lambda: client._new_msgs.append(reply))

        with self.assertLogs("client", level="DEBUG") as log_ctx:
            result = await client._send_to_server(ms, time_to_expire=0.05)

        self.assertIs(result, reply)
        self.assertEqual(client._new_msgs, [])
        self.assertEqual(client._waiting_amount, 0)
        self.assertTrue(any("was already in the mailbox" in msg for msg in log_ctx.output))

    async def test_no_reply_still_raises_timeout(self):
        """No reply anywhere -> CommunicationTimeoutError is still raised."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=2)

        self._patch_wait_for_response(schedule_append=None)

        with self.assertRaises(CommunicationTimeoutError):
            await client._send_to_server(ms, time_to_expire=0.05)

        self.assertEqual(client._new_msgs, [])
        self.assertEqual(client._waiting_amount, 0)

    async def test_foreign_reply_in_mailbox_is_not_mistaken(self):
        """Mailbox holds an envelope with another id at timeout -> still a timeout error, and the
        foreign envelope is left untouched in `_new_msgs`."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=3)
        foreign = self._make_envelope(create_time=time.time(), msg_id=999)

        self._patch_wait_for_response(schedule_append=lambda: client._new_msgs.append(foreign))

        with self.assertRaises(CommunicationTimeoutError):
            await client._send_to_server(ms, time_to_expire=0.05)

        self.assertEqual(client._new_msgs, [foreign])
        self.assertEqual(client._waiting_amount, 0)


class TestSendToServerCancellationSemantics(unittest.IsolatedAsyncioTestCase):
    """Cancellation-semantics tests for the `async with asyncio.timeout(...)` migration in
    `_send_to_server` (replacing the old shield/wait_for-based helper): result delivery,
    `TimeoutError` on timeout, and caller cancellation propagating `CancelledError` (not the
    awaited work's own exception) while the awaited work is actually cancelled."""

    @staticmethod
    def _make_client():
        return TestClientTimeoutMailboxCheck._make_client()

    @staticmethod
    def _make_envelope(create_time: float, msg_id: int):
        return TestClientTimeoutMailboxCheck._make_envelope(create_time, msg_id)

    async def test_result_delivered_when_response_arrives_in_time(self):
        """When the response arrives before the timeout, it is returned normally."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=10)
        reply = self._make_envelope(create_time=MessageSerializer.unpack_b(ms.create_time), msg_id=10)

        async def _fake_wait_for_response(self_inner, msg_create_time_b, msg_id_b):
            await asyncio.sleep(0)
            return reply

        original = _StubClient._wait_for_response
        _StubClient._wait_for_response = _fake_wait_for_response
        self.addCleanup(setattr, _StubClient, "_wait_for_response", original)

        result = await client._send_to_server(ms, time_to_expire=5)

        self.assertIs(result, reply)

    async def test_timeout_error_raised_when_no_response(self):
        """When nothing ever arrives, `CommunicationTimeoutError` is raised (built on
        `TimeoutError`, which is `asyncio.TimeoutError` since Python 3.11)."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=11)

        async def _fake_wait_for_response(self_inner, msg_create_time_b, msg_id_b):
            await asyncio.Event().wait()

        original = _StubClient._wait_for_response
        _StubClient._wait_for_response = _fake_wait_for_response
        self.addCleanup(setattr, _StubClient, "_wait_for_response", original)

        with self.assertRaises(CommunicationTimeoutError):
            await client._send_to_server(ms, time_to_expire=0.05)

    async def test_caller_cancelled_propagates_cancelled_error_and_cancels_inner_work(self):
        """When the caller of `_send_to_server` is cancelled (not a timeout firing), a plain
        `asyncio.CancelledError` propagates -- not the inner work's own exception -- and the
        awaited work is actually cancelled."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=12)

        inner_cancelled = asyncio.Event()

        async def _fake_wait_for_response(self_inner, msg_create_time_b, msg_id_b):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                inner_cancelled.set()
                raise

        original = _StubClient._wait_for_response
        _StubClient._wait_for_response = _fake_wait_for_response
        self.addCleanup(setattr, _StubClient, "_wait_for_response", original)

        task = asyncio.ensure_future(client._send_to_server(ms, time_to_expire=5))
        await asyncio.sleep(0)  # let the task start and reach the inner await
        task.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertTrue(inner_cancelled.is_set())
        self.assertEqual(client._waiting_amount, 0)


if __name__ == "__main__":
    unittest.main()
